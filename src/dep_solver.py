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

import msg as p


class IDependable:
    def __init__(self):
        self.dep_fixed = False;
        self.dep_index = 0;
        self.dep_provides = [];
        self.dep_requires = [];
        self.dep_depends_on = [];

class DependencySolver:
    def __init__(self):
        self.entities = {};
        from srcfile import SourceFileFactory
        self.sff = SourceFileFactory()

    def __lookup_post_provider(self, files, start_index, file):
        requires = file.dep_requires
        while True:
            start_index = start_index + 1
            try:
                if type(files[start_index]) == type(file):
                    f = files[start_index]
                else:
                    continue
            except IndexError:
                break

            if requires:
                for req in requires:
                    if req in f.dep_provides: 
                        return start_index
        return None

    def __find_provider_vhdl_file(self, files, req):
        for f in files:
            if req in f.dep_provides:
                return f

        return None

    def __find_provider_verilog_files(self, v_file):
        import os
        ret = []

        inc_dirs = self.__parse_vlog_opt(v_file.vlog_opt)

        for dir in inc_dirs:
            dir = os.path.join(vf_dirname, dir)
            if not os.path.exists(dir) or not os.path.isdir(dir):
                p.rawprint("WARNING: include path "+dir+" doesn't exist")

        for req in v_file.dep_requires: #find all required files
            for dir in [v_file.dirname]+inc_dirs:
                h_file = os.path.join(vf_dirname, req)
                if os.path.exists(h_file) and not os.path.isdir(h_file):
                    dep_file = self.sff.new(h_file)
                    #go recursively into all included files
                    ret.extend(self.__find_provider_verilog_files(dep_file))
                    ret.append(dep_file)
                    continue

            #if we reached this point, we didn't find anything
            p.rawprint("Cannot find include for file "+str(f)+": "+req)
        return ret

    def __parse_vlog_opt(self, vlog_opt):
        import re
        ret = []
        inc_pat = re.compile(".*?\+incdir\+([^ ]+)")
        while True:
            m = re.match(inc_pat, vlog_opt)
            if m:
                ret.append(m.group(1))
                vlog_opt = vlog_opt[m.end():]
            else:
                break
        return ret

    def solve(self, fileset):
        n_iter = 0
        max_iter = 100
        import copy

        fset = fileset.filter(IDependable);

        f_nondep = []

        done = False
        while not done and (n_iter < max_iter):
            n_iter = n_iter+1
            done = True
            for f in fset:
                if not f.dep_fixed:
                    idx = fset.index(f)
                    k = self.__lookup_post_provider(files=fset, start_index=idx, file=f);

                    if k:
                        done = False
                        #swap
                        fset[idx], fset[k] = fset[k], fset[idx]

        if(n_iter == max_iter):
            p.rawprint("Maximum number of iterations reached when trying to solve the dependencies."+
            "Perhaps a cyclic inter-dependency problem...");
            return None

        for f in fset:
            if f.dep_fixed:
                f_nondep.append(copy.copy(f))
                del f

        f_nondep.sort(key=lambda f: f.dep_index)

        from srcfile import VHDLFile, VerilogFile
        for f in [file for file in fset if isinstance(file, VHDLFile)]:
            p.vprint(f.path)
            if f.dep_requires:
                for req in f.dep_requires:
                    pf = self.__find_provider_vhdl_file([file for file in fset if isinstance(file, VHDLFile)], req)
                    if not pf:
                        p.rawprint("ERROR: Missing dependency in file "+str(f)+": " + req[0]+'.'+req[1])
                    else:
                        p.vprint("--> " + pf.path);
                        if pf.path != f.path:
                            f.dep_depends_on.append(pf)
            #get rid of duplicates by making a set from the list and vice versa
            f.dep_depends_on = list(set(f.dep_depends_on))

        import srcfile as sf

        for f in [file for file in fset if isinstance(file, VerilogFile)]:
            p.vprint(f.path)
            if f.dep_requires:
                for req in f.dep_requires:
                    files = self.__find_provider_verilog_files(f)
                    if not len(files):
                        p.vprint("--> " + pf.path)
                    f.dep_depends_on.extend(files)
            #get rid of duplicates by making a set from the list and vice versa
            f.dep_depends_on = list(set(f.dep_depends_on))

        newobj = sf.SourceFileSet();
        newobj.add(f_nondep);
        for f in fset:
            try:
                if not f.dep_fixed:
                    newobj.add(f)
            except:
                newobj.add(f)

        for k in newobj.files:
            p.vprint(str(k.dep_index) + " " + k.path + str(k.dep_fixed))
        return newobj
