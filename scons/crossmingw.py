"""SCons.Tool.gcc

Tool-specific initialization for MinGW (http://www.mingw.org/)

There normally shouldn't be any need to import this module directly.
It will usually be imported through the generic SCons.Tool.Tool()
selection method.

See also http://www.scons.org/wiki/CrossCompilingMingw
"""

#
# Copyright (c) 2001, 2002, 2003, 2004 The SCons Foundation
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY
# KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

import os
import os.path
import string

import SCons.Action
import SCons.Builder
import SCons.Tool
import SCons.Util

# This is what we search for to find mingw:
prefixes32 = SCons.Util.Split("""
    mingw32-
    mingw32msvc-
    i386-mingw32-
    i486-mingw32-
    i586-mingw32-
    i686-mingw32-
    i386-mingw32msvc-
    i486-mingw32msvc-
    i586-mingw32msvc-
    i686-mingw32msvc-
    i686-pc-mingw32-
    i686-w64-mingw32-
""")
prefixes64 = SCons.Util.Split("""
    x86_64-w64-mingw32-
    amd64-mingw32-
    amd64-mingw32msvc-
    amd64-pc-mingw32-
""")

def find(env):
    prefixes = prefixes64 if env['machine'] == 'x86_64' else prefixes32
    return next(
        (
            prefix
            for prefix in prefixes
            if env.WhereIs(f'{prefix}gcc')
            or SCons.Util.WhereIs(f'{prefix}gcc')
        ),
        '',
    )

def shlib_generator(target, source, env, for_signature):
    cmd = SCons.Util.CLVar(['$SHLINK', '$SHLINKFLAGS']) 

    if dll := env.FindIxes(target, 'SHLIBPREFIX', 'SHLIBSUFFIX'):
        cmd.extend(['-o', dll])
    cmd.extend(['$SOURCES', '$_LIBDIRFLAGS', '$_LIBFLAGS'])

    if implib := env.FindIxes(target, 'LIBPREFIX', 'LIBSUFFIX'):
        cmd.append(f'-Wl,--out-implib,{implib.get_string(for_signature)}')
    if def_target := env.FindIxes(target, 'WIN32DEFPREFIX', 'WIN32DEFSUFFIX'):
        cmd.append(f'-Wl,--output-def,{def_target.get_string(for_signature)}')
    return [cmd]

def shlib_emitter(target, source, env):
    dll = env.FindIxes(target, 'SHLIBPREFIX', 'SHLIBSUFFIX')
    no_import_lib = env.get('no_import_lib', 0)

    if not dll:
        raise (
            SCons.Errors.UserError,
            f'A shared library should have exactly one target with the suffix: {env.subst("$SHLIBSUFFIX")}',
        )

    if not no_import_lib and \
       not env.FindIxes(target, 'LIBPREFIX', 'LIBSUFFIX'):

        # Append an import library to the list of targets.
        target.append(env.ReplaceIxes(dll,  
                                      'SHLIBPREFIX', 'SHLIBSUFFIX',
                                      'LIBPREFIX', 'LIBSUFFIX'))

    # Append a def file target if there isn't already a def file target
    # or a def file source. There is no option to disable def file
    # target emitting, because I can't figure out why someone would ever
    # want to turn it off.
    def_source = env.FindIxes(source, 'WIN32DEFPREFIX', 'WIN32DEFSUFFIX')
    def_target = env.FindIxes(target, 'WIN32DEFPREFIX', 'WIN32DEFSUFFIX')
    if not def_source and not def_target:
        target.append(env.ReplaceIxes(dll,  
                                      'SHLIBPREFIX', 'SHLIBSUFFIX',
                                      'WIN32DEFPREFIX', 'WIN32DEFSUFFIX'))

    return (target, source)
                         

shlib_action = SCons.Action.Action(shlib_generator, '$SHLINKCOMSTR', generator=1)

res_action = SCons.Action.Action('$RCCOM', '$RCCOMSTR')

res_builder = SCons.Builder.Builder(action=res_action, suffix='.o',
                                    source_scanner=SCons.Tool.SourceFileScanner)
SCons.Tool.SourceFileScanner.add_scanner('.rc', SCons.Defaults.CScan)



def generate(env):
    mingw_prefix = find(env)

    if mingw_prefix:
        dir = os.path.dirname(
            env.WhereIs(f'{mingw_prefix}gcc')
            or SCons.Util.WhereIs(f'{mingw_prefix}gcc')
        )

        # The mingw bin directory must be added to the path:
        path = env['ENV'].get('PATH', [])
        if not path: 
            path = []
        if SCons.Util.is_String(path):
            path = string.split(path, os.pathsep)

        env['ENV']['PATH'] = string.join([dir] + path, os.pathsep)

    # Most of mingw is the same as gcc and friends...
    gnu_tools = ['gcc', 'g++', 'gnulink', 'ar', 'gas']
    for tool in gnu_tools:
        SCons.Tool.Tool(tool)(env)

    #... but a few things differ:
    env['CC'] = f'{mingw_prefix}gcc'
    env['SHCCFLAGS'] = SCons.Util.CLVar('$CCFLAGS')
    env['CXX'] = f'{mingw_prefix}g++'
    env['SHCXXFLAGS'] = SCons.Util.CLVar('$CXXFLAGS')
    env['SHLINKFLAGS'] = SCons.Util.CLVar('$LINKFLAGS -shared')
    env['SHLINKCOM']   = shlib_action
    env.Append(SHLIBEMITTER = [shlib_emitter])
    env['LINK'] = f'{mingw_prefix}g++'
    env['AR'] = f'{mingw_prefix}ar'
    env['RANLIB'] = f'{mingw_prefix}ranlib'
    env['LINK'] = f'{mingw_prefix}g++'
    env['AS'] = f'{mingw_prefix}as'
    env['WIN32DEFPREFIX']        = ''
    env['WIN32DEFSUFFIX']        = '.def'
    env['SHOBJSUFFIX'] = '.o'
    env['STATIC_AND_SHARED_OBJECTS_ARE_THE_SAME'] = 1

    env['RC'] = f'{mingw_prefix}windres'
    env['RCFLAGS'] = SCons.Util.CLVar('')
    env['RCCOM'] = '$RC $_CPPDEFFLAGS $_CPPINCFLAGS ${INCPREFIX}${SOURCE.dir} $RCFLAGS -i $SOURCE -o $TARGET'
    env['BUILDERS']['RES'] = res_builder

    # Some setting from the platform also have to be overridden:
    env['OBJPREFIX']      = ''
    env['OBJSUFFIX']      = '.o'
    env['SHOBJPREFIX']    = '$OBJPREFIX'
    env['SHOBJSUFFIX']    = '$OBJSUFFIX'
    env['PROGPREFIX']     = ''
    env['PROGSUFFIX']     = '.exe'
    env['LIBPREFIX']      = 'lib'
    env['LIBSUFFIX']      = '.a'
    env['SHLIBPREFIX']    = ''
    env['SHLIBSUFFIX']    = '.dll'
    env['LIBPREFIXES']    = [ 'lib', '' ]
    env['LIBSUFFIXES']    = [ '.a', '.lib' ]

def exists(env):
    return find(env)
