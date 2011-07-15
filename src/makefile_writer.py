#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2011 Pawel Szostek (pawel.szostek@cern.ch)
#
#    This source code is free software; you can redistribute it
#    and/or modify it in source code form under the terms of the GNU
#    General Public License as published by the Free Software
#    Foundation; either version 2 of the License, or (at your option)
#    any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA
#

import os
import string

class MakefileWriter(object):
    def __init__(self, filename):
        self._file = None
        self._filename = filename
        self._is_initialized = False

    def __del__(self):
        if self._is_initialized:
            self._file.close()

    def initialize(self):
        if not self._is_initialized:
            self._file = open(self._filename, "w")
            self.writeln("########################################")
            self.writeln("#  This file was generated by hdlmake  #")
            self.writeln("#  http://ohwr.org/projects/hdl-make/  #")
            self.writeln("########################################")
            self.writeln()
            self._is_initialized = True
        else:
            pass

    def write(self, line=None):
        self._file.write(line)

    def writeln(self, text=None):
        if text == None:
            self._file.write("\n")
        else:
            self._file.write(text+"\n")

    def reset_file(self, filename):
        self._file.close()
        self._file = open(filename, "w")

    def generate_remote_synthesis_makefile(self, files, name, cwd, user, server, ise):
        import path 
        if name == None:
            import random
            name = ''.join(random.choice(string.ascii_letters + string.digits) for x in range(8))
        user_tmpl = "USER:={0}"
        server_tmpl = "SERVER:={0}"
        remote_name_tmpl = "R_NAME:={0}"
        files_tmpl = "FILES := {0}"

        if  user == None:
            user_tmpl = user_tmpl.format("$(HDLMAKE_USER)#take the value from the environment")
            test_tmpl = """__test_for_remote_synthesis_variables:
ifeq (x$(USER),x)
\t@echo "Remote synthesis user is not set. You can set it by editing variable USER in the makefile." && false
endif
ifeq (x$(SERVER),x)
\t@echo "Remote synthesis server is not set. You can set it by editing variable SERVER in the makefile." && false
endif
"""
        else:
            user_tmpl = user_tmpl.format(user)
            test_tmpl = "__test_for_remote_synthesis_variables:\n\t\ttrue #dummy\n"
            
        if server == None:
            server_tmpl = server_tmpl.format("$(HDLMAKE_SERVER)#take the value from the environment")
        else:
            server_tmpl = server_tmpl.format(server)
            
        remote_name_tmpl = remote_name_tmpl.format(name)
        self.initialize()
        self.writeln(user_tmpl)
        self.writeln(server_tmpl)
        self.writeln(remote_name_tmpl)
        self.writeln()
        self.writeln(test_tmpl)
        self.writeln("CWD := $(shell pwd)")
        self.writeln("")
        self.writeln(files_tmpl.format(' \\\n'.join([s.rel_path() for s in files])))
        self.writeln("")
        self.writeln("#target for running simulation in the remote location")
        self.writeln("remote: __test_for_remote_synthesis_variables __send __do_synthesis __send_back")
        self.writeln("__send_back: __do_synthesis")
        self.writeln("__do_synthesis: __send")
        self.writeln("__send: __test_for_remote_synthesis_variables")
        self.writeln("")

        mkdir_cmd = "ssh $(USER)@$(SERVER) 'mkdir -p $(R_NAME)'"
        rsync_cmd = "rsync -Rav $(foreach file, $(FILES), $(shell readlink -f $(file))) $(USER)@$(SERVER):$(R_NAME)"
        send_cmd = "__send:\n\t\t{0}\n\t\t{1}".format(mkdir_cmd, rsync_cmd)
        self.writeln(send_cmd)
        self.writeln("")

        tcl = "run.tcl"
        synthesis_cmd = "__do_synthesis:\n\t\t"
        synthesis_cmd += "ssh $(USER)@$(SERVER) 'cd $(R_NAME)$(CWD) && {0}xtclsh {1}'"

        try:
            self.writeln(synthesis_cmd.format(path.ise_path_32[str(ise)]+'/', tcl))
        except KeyError:
            self.writeln(synthesis_cmd.format("", tcl))
        self.writeln()
 
        send_back_cmd = "__send_back: \n\t\tcd .. && rsync -av $(USER)@$(SERVER):$(R_NAME)$(CWD) . && cd $(CWD)"
        self.write(send_back_cmd)
        self.write("\n\n")

        cln_cmd = "cleanremote:\n\t\tssh $(USER)@$(SERVER) 'rm -rf $(R_NAME)'"
        self.writeln("#target for removing stuff from the remote location")
        self.writeln(cln_cmd)
        self.writeln()

    def generate_quartus_makefile(self, top_mod):
        pass

    def generate_ise_makefile(self, top_mod, ise):
        import path 
        mk_text = """PROJECT := """ + top_mod.syn_project + """
ISE_CRAP := \
*.bgn \
*.html \
*.tcl \
*.bld \
*.cmd_log \
*.drc \
*.lso \
*.ncd \
*.ngc \
*.ngd \
*.ngr \
*.pad \
*.par \
*.pcf \
*.prj \
*.ptwx \
*.stx \
*.syr \
*.twr \
*.twx \
*.gise \
*.unroutes \
*.ut \
*.xpi \
*.xst \
*_bitgen.xwbt \
*_envsettings.html \
*_guide.ncd \
*_map.map \
*_map.mrp \
*_map.ncd \
*_map.ngm \
*_map.xrpt \
*_ngdbuild.xrpt \
*_pad.csv \
*_pad.txt \
*_par.xrpt \
*_summary.html \
*_summary.xml \
*_usage.xml \
*_xst.xrpt \
usage_statistics_webtalk.html \
webtalk.log \
webtalk_pn.xml \
run.tcl

#target for performing local synthesis
local:
\t\techo "project open $(PROJECT)" > run.tcl
\t\techo "process run {Generate Programming File} -force rerun_all" >> run.tcl
"""
        xtcl = "\t\txtclsh run.tcl"
        mk_text2 = """
#target for cleaing all intermediate stuff
clean:
\t\trm -f $(ISE_CRAP)
\t\trm -rf xst xlnx_auto_*_xdb iseconfig _xmsgs _ngo
    
#target for cleaning final files
mrproper:
\t\trm -f *.bit *.bin *.mcs

"""
        self.initialize()
        self.write(mk_text)
        self.writeln(xtcl)
        self.write(mk_text2)

    def generate_fetch_makefile(self, modules_pool):
        rp = os.path.relpath
        self.initialize()
        self.write("#target for fetching all modules stored in repositories\n")
        self.write("fetch: ")
        self.write(' \\\n'.join(["__"+m.basename+"_fetch" for m in modules_pool if m.source in ["svn","git"]]))
        self.write("\n\n")

        for module in modules_pool:
            basename = module.basename
            if module.source == "svn":
                self.write("__"+basename+"_fetch:\n")
                self.write("\t\t")
                self.write("PWD=$(shell pwd); ")
                self.write("cd " + rp(module.fetchto) + '; ')
                c = "svn checkout {0}{1} {2};"
                if module.revision:
                    c=c.format(module.url, "@"+module.revision, module.basename)
                else:
                    c=c.format(module.url, "", module.basename)
                self.write(c)
                self.write("cd $(PWD) \n\n")

            elif module.source == "git":
                self.write("__"+basename+"_fetch:\n")
                self.write("\t\t")
                self.write("PWD=$(shell pwd); ")
                self.write("cd " + rp(module.fetchto) + '; ')
                self.write("if [ -d " + basename + " ]; then cd " + basename + '; ')
                self.write("git pull; ")
                if module.revision:
                    self.write("git checkout " + module.revision +';')
                self.write("else git clone "+ module.url + '; fi; ')
                if module.revision:
                    self.write("git checkout " + module.revision + ';')
                self.write("cd $(PWD) \n\n")

    def generate_modelsim_makefile(self, fileset, top_module):
        from srcfile import VerilogFile, VHDLFile
        make_preambule_p1 = """## variables #############################
PWD := $(shell pwd)
WORK_NAME := work

MODELSIM_INI_PATH := """ + self.__modelsim_ini_path() + """

VCOM_FLAGS := -nologo -quiet -modelsimini ./modelsim.ini
VSIM_FLAGS := 
VLOG_FLAGS := -nologo -quiet -sv -modelsimini $(PWD)/modelsim.ini """ + self.__get_rid_of_incdirs(top_module.vlog_opt) + """
""" 
        make_preambule_p2 = """## rules #################################
sim: modelsim.ini $(LIB_IND) $(VERILOG_OBJ) $(VHDL_OBJ)
$(VERILOG_OBJ): $(VHDL_OBJ) 
$(VHDL_OBJ): $(LIB_IND) modelsim.ini

modelsim.ini: $(MODELSIM_INI_PATH)/modelsim.ini
\t\tcp $< .
clean:
\t\trm -rf ./modelsim.ini $(LIBS) $(WORK_NAME)
.PHONY: clean

"""
        #open the file and write the above preambule (part 1)
        self.initialize()
        self.write(make_preambule_p1)

        rp = os.path.relpath
        self.write("VERILOG_SRC := ")
        for vl in fileset.filter(VerilogFile):
            self.write(vl.rel_path() + " \\\n")
        self.write("\n")

        self.write("VERILOG_OBJ := ")
        for vl in fileset.filter(VerilogFile):
            #make a file compilation indicator (these .dat files are made even if
            #the compilation process fails) and add an ending according to file's
            #extension (.sv and .vhd files may have the same corename and this
            #causes a mess
            self.write(os.path.join(vl.library, vl.purename, "."+vl.purename+"_sv") + " \\\n")
        self.write('\n')

        libs = set(f.library for f in fileset.files)

        self.write("VHDL_SRC := ")
        for vhdl in fileset.filter(VHDLFile):
            self.write(vhdl.rel_path() + " \\\n")
        self.writeln()

        #list vhdl objects (_primary.dat files)
        self.write("VHDL_OBJ := ")
        for vhdl in fileset.filter(VHDLFile):
            #file compilation indicator (important: add _vhd ending)
            self.write(os.path.join(vhdl.library, vhdl.purename,"."+vhdl.purename+"_vhd") + " \\\n")
        self.write('\n')

        self.write('LIBS := ')
        self.write(' '.join(libs))
        self.write('\n')
        #tell how to make libraries
        self.write('LIB_IND := ')
        self.write(' '.join([lib+"/."+lib for lib in libs]))
        self.write('\n')
        self.write(make_preambule_p2)

        for lib in libs:
            self.write(lib+"/."+lib+":\n")
            self.write(' '.join(["\t(vlib",  lib, "&&", "vmap", "-modelsimini modelsim.ini", 
            lib, "&&", "touch", lib+"/."+lib,")"]))

            self.write(' '.join(["||", "rm -rf", lib, "\n"]))
            self.write('\n')

        #rules for all _primary.dat files for sv
        for vl in fileset.filter(VerilogFile):
            self.write(os.path.join(vl.library, vl.purename, '.'+vl.purename+"_sv")+': ')
            self.write(vl.rel_path() + ' ')
            self.writeln(' '.join([f.rel_path() for f in vl.dep_depends_on]))
            self.write("\t\tvlog -work "+vl.library+" $(VLOG_FLAGS) +incdir+"+rp(vl.dirname)+" ")
            self.write(vl.vlog_opt+" $<")
            self.write(" && mkdir -p "+os.path.join(vl.library+'/'+vl.purename) )
            self.write(" && touch "+ os.path.join(vl.library, vl.purename, '.'+vl.purename+"_sv")+'\n\n')
        self.write("\n")

        #list rules for all _primary.dat files for vhdl
        for vhdl in fileset.filter(VHDLFile):
            lib = vhdl.library
            purename = vhdl.purename 
            #each .dat depends on corresponding .vhd file
            self.write(os.path.join(lib, purename, "."+purename+"_vhd") + ": "+vhdl.rel_path()+'\n')
            self.write(' '.join(["\t\tvcom $(VCOM_FLAGS)", vhdl.vcom_opt, "-work", lib, vhdl.rel_path(),
            "&&", "mkdir -p", os.path.join(lib, purename), "&&", "touch", os.path.join(lib, purename, '.'+ purename+"_vhd"), '\n']))
            self.write('\n')
            if len(vhdl.dep_depends_on) != 0:
                self.write(os.path.join(lib, purename, "."+purename) +":")
                for dep_file in vhdl.dep_depends_on:
                    name = dep_file.purename
                    self.write(" \\\n"+ os.path.join(dep_file.library, name, "."+name))
                self.write('\n\n')

    def __get_rid_of_incdirs(self, vlog_opt):
        vlog_opt = self.__emit_string(vlog_opt)
        vlogs = vlog_opt.split(' ')
        ret = []
        for v in vlogs:
            if not v.startswith("+incdir+"):
                ret.append(v)
        return ' '.join(ret)

    def __emit_string(self, s):
        if not s:
            return ""
        else:
            return s

    def __modelsim_ini_path(self):
        vsim_path = os.popen("which vsim").read().strip()
        bin_path = os.path.dirname(vsim_path)
        return os.path.abspath(bin_path+"/../")
