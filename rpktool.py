# /usr/bin/python3
# -*- coding: utf-8 -*- 

# Copyright (C) 2020 OPPO. All rights reserved.
#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os
import sys
import re

import chardet
import zipfile
import shutil

import jsbeautifier
import argparse
import demjson

from colorama import init, Fore, Back, Style
from tqdm import *

import datetime


class Rpktool:


    file_type = 'js'
    pkg_name = ''
    file_path = ''
    output_path = ''
    tool_name = 'com.rpktool.debug'
    tool_path = './debug/'
    tool_debug_path ='./debug/dist/'
    webpack_conf_path = './debug/node_modules/hap-toolkit/tools/packager/webpack.config.js'
    def __init__(self, file_path, file_type, del_flag = False ):
        # debug switch
        self.log = Print(True)
        self.file_path = file_path
        self.file_type = file_type
        self.pkg_name = ''
        self.rpk_name = ''
        self.version = ''
        self.tool_name = 'com.rpktool.debug'
        self.tool_debug_path ='./debug/dist/'
        self.tool_path = './debug/'
        self.pack_output = ''
        self.del_flag = del_flag
        self.webpack_conf_path = './debug/node_modules/hap-toolkit/tools/packager/webpack.config.js'
        self.rpk_feature_list = []
        self.features_chinese_list = {}
        self.features_keyword_list = {}
        self.feat_conf_path = './feat_conf'
        self.os_name = os.name
        self.rpk_type = 1
        self.background_feature_list = []
        self.log_level =''
        self.isdebug = ''
        self.manifest_path = ''


    def process_rpk(self):
        if not self.extract_rpk():
            return False

        if not self.__reformat():
            return False

        return True

    def extract_rpk(self):
        # abspath of rpk
        rpk_file = self.file_path
        return self.__unzip_rpk(rpk_file)
    
    def __unzip(self, file_path, out_path=None):

        if out_path:
            dir_name = out_path
        else:
            dir_name = os.path.splitext(file_path)[0]

        try:
            rf = zipfile.ZipFile(file_path)
            os.mkdir(dir_name)
            rf.extractall(dir_name)
            rf.close()
        except:
            self.log.error("Can't extract RPK file: "+file_path)

    def __unzip_rpk(self, rpk_path):
        # abspath of rpk
        rpk_file = rpk_path
        rpk_path = os.path.dirname(rpk_file)
        rpk_file_name = os.path.basename(rpk_file)
        temp_path = os.path.join(rpk_path, os.path.splitext(rpk_file_name)[0]) + '_temp'
        try:
            self.__unzip(rpk_file, temp_path)
        except:
            self.del_flag = True

        # Unzip sub rpks if it's a mult_package rpk
        for root, dirs, files in os.walk(temp_path):
            for name in files:
                if name.endswith(".rpk"):
                    try:
                        self.__unzip(os.path.join(root, name))
                    except:
                        self.del_flag = True

        manifest_path = self.__get_manifest_path(temp_path)
        try:
            ret_with_error = False
            ret_get_info = self.__get_pkg_info(manifest_path)
            if not ret_get_info:
                self.log.error("Can't get RPK info, delete temp file(s)...")
                self.del_flag = not ret_get_info
                ret_with_error = not ret_get_info
        except:
            self.log.error("Can't get RPK info, delete temp file(s)...")
            self.del_flag = True
            ret_with_error = True
        new_rpk_path = os.path.join(rpk_path, self.pkg_name) + '_rpk'
        if self.del_flag:
            # For debugging and scanning, this dir will be deleted after we got the info of rpk.
            try:
                self.log.verbose("delete temp files...")
                shutil.rmtree(temp_path)
            except:
                self.log.error("Failed to delete temp files. Please check if the file(s) is in use.")
                return False
            if ret_with_error:
                return False
            else:
                return True
        # Only it's not in debug mode can delete exist dir
        elif os.path.exists(new_rpk_path):
            self.log.error("Delete exist dir "+ new_rpk_path)
            try:
                shutil.rmtree(new_rpk_path)
            except:
                self.log.error("Failed to delete the dir. Please check if the file(s) is in use.")
                return False

        os.rename(temp_path, new_rpk_path)
        self.output_path = new_rpk_path
        return True

    def __get_pkg_info(self, manifest_path):
        if os.path.exists(manifest_path):
            with open(manifest_path, 'r') as fjson:
                tjson = fjson.read()
                strjson = demjson.decode(tjson)
                self.pkg_name = strjson['package']
                self.version = strjson['versionName']
                self.rpk_name = strjson['name']

                # get features info
                if 'type' in strjson:
                    if strjson['type'] == 'game':
                        # for quickgame，TODO a lot
                        self.rpk_type = 'game'
                self.rpk_type = 'app'

                if 'features' in strjson:
                    features = strjson['features']
                    for feature in features:
                        self.rpk_feature_list.append(feature['name'])

                if 'config' in strjson:
                    configs = strjson['config']
                    if 'logLevel' in configs:
                        self.log_level=configs['logLevel']
                    if 'debug' in configs:
                        self.isdebug=configs['debug']
                    if 'background' in configs:
                        background = configs['background']
                        background_features = background['features']
                        for background_feature in background_features:
                            self.background_feature_list.append(background_feature)

                return True
        else:
            self.log.error("It's seems not a rpk file.")
            return False

    def __reformat(self):
        root_dir = self.output_path
        file_type = self.file_type
        if not self.reformat_files(root_dir, file_type):
            return False
        self.__replase_js_file(root_dir)
        return True

    def __replase_js_file(self, path):
        '''
        replace origin js by the reformated js, eg. index_new.js --> index.js
        '''
        for root, dirs, files in os.walk(path):
            for name in files:
                # origin js file
                if name.endswith(".js") and not name.endswith("_new.js"):
                    os.remove(os.path.join(root, name))
                    os.rename(os.path.join(root, name).replace('.js','_new.js'),os.path.join(root, name))

    @staticmethod
    def __reformat_eval(content):
        '''
        format js which created by webpack conf [devtool: eval]
        @param str content : content to be reformated
        @return str content : reformated content
        @return bool is_eval : Judge whether it is created by webpack conf [devtool: eval]
        '''
        if "eval(" in content:
            if re.findall("__webpack_require__\(moduleId\)", content):
                if re.findall("eval\(\".*\"\);\n", content):
                    return re.sub("eval\(\".*\"\);\n", Rpktool.__re_eval, content), True
        return content, False
        
    @staticmethod
    def __re_eval(matched):
        content = matched.group()
        content = content.replace('\\\\n','\\ n')
        content = content.replace("\\n","\n").replace('\\"','"').replace('\\\\\"','\\\"')
        content = content.replace('\\ n','\\n')
        # del 'eval();'
        ret = content[6:-4]
        return ret

    # @staticmethod
    # def reformat_file(rootDir, file_type):
    #     print("@")
    #     dir_list = os.listdir(rootDir)
    #     for i in range(0,len(dir_list)):
    #         path = os.path.join(rootDir,dir_list[i])
    #         if os.path.isfile(path):
    #             if path.endswith('.'+file_type):
    #                 if not path.endswith('_new.'+file_type):
    #                     with open(path , 'rt') as ft:
    #                         content = ft.read()
    #                         if not type(content) is str:
    #                             result = chardet.detect(content)
    #                             coding = result.get('encoding')
    #                             # encode file if the format is not utf-8
    #                             if coding != 'utf-8':
    #                                 content = content.decode(coding).encode('utf-8')
    #                     # reformat eval javascript file frist
    #                     content, is_eval = Rpktool.__reformat_eval(content)
    #                     if not is_eval:
    #                         content = jsbeautifier.beautify(content)
    #                     jsFileName = path[:-3] + '_new.' +file_type
    #                     with open(jsFileName, 'w+') as fp:
    #                         fp.write(content)
    #                         print(Fore.LIGHTBLACK_EX+ "[+]reformating " + path+" success." +50*" " + "\r", end='')
                        
    #         elif os.path.isdir(path):
    #             if not 'node_modules' in path:
    #                 Rpktool.reformat_file(path, file_type)
    #     return True
    @staticmethod
    def reformat_file(root_dir, file_type):
        try:
            with open(root_dir , 'rt') as ft:
                content = ft.read()
                if not type(content) is str:
                    result = chardet.detect(content)
                    coding = result.get('encoding')
                    # encode file if the format is not utf-8
                    if coding != 'utf-8':
                        content = content.decode(coding).encode('utf-8')
            # reformat eval javascript file frist
            content, is_eval = Rpktool.__reformat_eval(content)
            if not is_eval:
                content = jsbeautifier.beautify(content)
            jsFileName = root_dir[:-3] + '_new.' +file_type
            with open(jsFileName, 'w+') as fp:
                fp.write(content)
            return True
        except:
            return False
        


    @staticmethod
    def reformat_files(root_dir, file_type='js'):
        file_path_list = Rpktool.detect_js_file(root_dir)
        process_bar = tqdm(file_path_list, desc=Fore.LIGHTBLACK_EX+'[+]reformating ')
        for file_path in process_bar:
            ret = Rpktool.reformat_file(file_path, file_type)
            #process_bar.set_description(file_path+'\r\n')
            if not ret:
                return False
            out_str = "\r[+]reformating: " +file_path
        print(Fore.GREEN + "[*]reformating js file successed!")
        return True
            


    @staticmethod
    def detect_js_file(root_dir, file_type='js'):
        file_path_list = []
        for root, dirs, files in os.walk(root_dir):
            for name in files:
                if name.endswith("." + file_type):
                    if not name.endswith('_new.' + file_type):
                        if not 'node_modules' in os.path.join(root, name):
                            file_path_list.append(os.path.join(root, name))
        return file_path_list

    
    def __mod_manifest(self, new_pkg_name):
        path = self.tool_path + '/src/'
        for rt, dirs, files, in os.walk(path):
            for f in files:
                if f == 'manifest.json':
                    self.__mod_file_by_regex(os.path.join(rt,f), '"package":\s"(\w*.)*"', '"package": '+'"'+new_pkg_name+'"')
                    '''with open(os.path.join(rt,f), 'r') as f1,open(os.path.join(rt,"%s.bak" % f), 'w') as f2:
                        for line in f1:
                            f2.write(re.sub('"package":\s"(\w*.)*"', '"package": '+'"'+new_pkg_name+'"',line))
                    os.remove(os.path.join(rt,f))
                    os.rename(os.path.join(rt,"%s.bak" % f), os.path.join(rt,f))'''
                    return True
        return False
    
    def __init_debug_tool(self):
        self.log.info("Initializing debug&pack tool:")
        if self.os_name=='nt':
            os.system("echo.|hap init debug&&cd ./debug&&npm install&&npm run build")
        else:
            os.system("echo |hap init debug&&cd ./debug&&npm install&&npm run build")

        # check dependencies for debug
        if not os.path.exists("./debug/node_modules"):
            self.log.error("Failed to init debug&pack tool!")
            return False
        else:
            self.log.info("Initializing debug&pack tool success.")
            return True

    def __mod_file_by_regex(self, file_path, regex_str,  mod_str):
        f = file_path
        # add for uincode
        if repr(mod_str).startswith("u'"):
            mod_str_esp = repr(mod_str)[2:-1]
        else:
            mod_str_esp = repr(mod_str)[1:-1]
        with open(file_path, 'r') as f1, open("%s.bak"%file_path, 'w') as f2:
            # add repr to avoid str escaping
            f2.write(re.sub(regex_str, mod_str_esp, f1.read()))
        os.remove(file_path)
        os.rename("%s.bak" % file_path, file_path)
        return True

    def debug_rpk(self):
        if self.rpk_type == 'game':
            self.log.info('Please open quickgame with runtime.apk in your device, then replace {IP_of_you_phone} in this url and open it in Chrome to debug:'+' '*10+Fore.CYAN+'chrome-devtools://devtools/bundled/inspector.html?v8only=true&ws='+Fore.LIGHTBLACK_EX+'{IP_of_you_phone}'+Fore.CYAN+':12345/00010002-0003-4004-8005-000600070008')
            return

        elif self.rpk_type == 'app':
            # if the debug tool hasn't be created
            if not os.path.exists("./debug/node_modules"):
                if not self.__init_debug_tool():
                    return False
            # modefine packagename in manifest.json 
            self.__mod_manifest(self.pkg_name)
            debug_name = self.tool_debug_path + self.pkg_name + '.debug.rpk'
            # Copy rpk to debug path if there are not the same file.
            if not os.path.abspath(self.file_path) == os.path.abspath(debug_name):
                # Delete old rpk in debug path if exists
                if os.path.exists(debug_name):
                    self.log.error("Delete exist debug rpk "+ debug_name)
                    os.remove(debug_name)
                shutil.copyfile(self.file_path, debug_name)
            # Run in new CMD window
            #os.system('start cmd /k \"cd ./debug/ & npm run server\"')
            # Run in old window
            self.log.verbose("Debug_server info:")
            try:
                os.system("cd ./debug/ && npm run server")
            except:
                self.log.error("Debug_server exit.")
            finally:
                return
        else:
            self.log.error("Unknown tpye of rpk, debugger exit.")
            return

    def __escape_path(self, path):
        return path.replace('\\', '/').strip()

    def __mod_pack_conf(self):
        f = self.webpack_conf_path
        # replace data has been tested in MacOS，hap-toolkit@0.6.15：
        regex_str = 'new\sZipPlugin(?:.|\n)*,'
        if not os.path.exists(f):
            f = './debug/node_modules/@hap-toolkit/packager/lib/webpack.post.js'
            regex_str ='new\sZipPlugin(?:.|\n)*\}\),'
            if not os.path.exists(f):
                self.log.error(" Error version of hap-toolkit.")
                exit()
        path_dist = self.__escape_path(os.path.abspath(self.tool_debug_path))
        pack_path = self.__escape_path(os.path.abspath(self.file_path))
        # versionCode unclear
        mod_str = '''new ZipPlugin({name: "'''+self.pkg_name+'''",
            icon: r,
            versionCode: "'''+self.version+'''",
            output: "'''+path_dist+'''",
            pathBuild: "'''+pack_path+'''",
            pathSignFolder: a,
            sign: "debug",
            priorities: m,
            subpackages: c,
            comment: S,
            cwd: i,
            disableStreamPack: n.disableStreamPack,
            disableSubpackages: n.disableSubpackages
        }),'''
        self.__mod_file_by_regex(f, regex_str, mod_str)
        return True

    def __get_manifest_path(self, file_path):
        if self.manifest_path == '':
            for root, dirs, files in os.walk(file_path):
                for name in files:
                    if name == "manifest.json":
                        self.manifest_path = os.path.join(root, name)
        return self.manifest_path

    def pack_rpk(self):
        # get info of pkg from manifest frist.
        manifest_path = self.__get_manifest_path(self.file_path)
        if not self.__get_pkg_info(manifest_path):
            self.log.error("Failed to repack this rpk, maybe it is not a quickapp dir ?")
            return False

        if self.rpk_type == 'game':
            # We can't pack a quick game now. #TODO
            self.log.error("Failed to repack this rpk because it is a quickgame and rpktool doesn't support yet.")
            return

        # check ./debug/ if is exists
        if not os.path.exists("./debug/node_modules") :
            self.__init_debug_tool()
            if not os.path.exists("./debug/node_modules"):
                self.log.error("Can't init debug&pack tool!")
                return False

        # mod webpack.config
        self.__mod_pack_conf()

        # Delete .\META-INF\CERT if exists
        if os.path.exists(self.file_path+'/META-INF/'):
            self.log.info("Delete /META-INF/CERT")
            try:
                shutil.rmtree(self.file_path+'/META-INF/')
            except:
                self.log.error("Failed to delete META-INF. Please delete it by youself.")
                return False
        self.log.info("Packing "+ Fore.CYAN+ self.file_path+Fore.LIGHTYELLOW_EX+":")

        # start build
        os.system("cd ./debug/ && npm run build")
        self.pack_output = self.tool_debug_path + self.pkg_name + ".debug.rpk"
        if not os.path.exists(self.pack_output):
            self.log.error('Failed to packing your files. Please delete this dir:"rpktool/debug/" and try again.')
            return False
        return True

    # add for print features
    def print_features(self, Report):
        if not self.__read_feat_conf():
            return False
        result = ''

        for feature in self.rpk_feature_list:
            for feature_chinese in self.features_chinese_list:
                if feature_chinese["feature"]==feature:
                    result = "   Using feature <"+feature+"> as <"+feature_chinese["content"]+">"
                    self.log.info(result)
                    result +='\n'
                    if Report:
                        Report.write_report(result)

        # print background features
        if self.background_feature_list:
            self.log.verbose("Found background feature(s):")
            for feature in self.background_feature_list:
                for feature_chinese in self.features_chinese_list:
                    if feature_chinese["feature"]==feature:
                        result = "   Using background feature <"+feature+"> as <"+feature_chinese["content"]+">"
                        self.log.info(result)
                        result +='\n'
                        if Report:
                            Report.write_report(result)
        return True
        
    def print_rpk_info(self, write_report_flag=False):
        self.log.info("QuickApp packgae name:"+Fore.CYAN+ self.pkg_name)
        self.log.info("QuickApp name:"+Fore.CYAN+ self.rpk_name)
        self.log.info("QuickApp version:"+Fore.CYAN+ self.version)
        if write_report_flag:
            self.log.verbose("Features:"+'\n')
            result ="QuickApp packgae name: "+self.pkg_name+"\n"
            result+="QuickApp name: "+self.rpk_name+'\n'
            result+="QuickApp version:"+self.version+"\n"
            result+="Features:"+'\n'
            return result
        else:
            return True

    # read conf from file
    def __read_feat_conf(self):
        config_path = self.feat_conf_path
        with open(config_path, 'rb') as f:
            lines = f.read()
            conf_content = demjson.decode(lines)
            self.features_chinese_list = conf_content['chinese']
            self.features_keyword_list = conf_content['regexes']
        return True



class Print:
    def __init__(self, isdebug=False):
        self.isdebug = isdebug

    def info(self, string):
        print(Fore.LIGHTYELLOW_EX + '[+] ' + string)

    def error(self, string):
        print(Fore.RED + '[!] ' + string)

    def debug(self, string):
        if self.isdebug:
            print(Fore.CYAN + '[D] ' + string)

    def verbose(self, string):
        print(Fore.GREEN + '[*] ' + string)

    def minor(self,string):
        print(Fore.CYAN + '[+] ' + string)



# Write report
class Report:
    def __init__(self, report_path):
        self.report_path = report_path
        self.report_file = open(self.report_path,'w+')

    def __del__(self):
        if not self.report_file.closed:
            self.report_file.close()

    def write_report(self, content):
        self.report_file.write(content)


def main():
    # reload(sys)
    # sys.setdefaultencoding( "utf-8" )
    log = Print(False)
    init(autoreset=True)
    parser = argparse.ArgumentParser()
    parser.add_argument("path" ,help="path of file/dir you want to process.")
    parser.add_argument("-j", "--js",action="store_true", default=False, help="reformat only .js files, it requires the path of .js as a parameter.")
    parser.add_argument("-d", "--debug",action="store_true", default=False, help="debug the rpk by haptoolkit.")
    parser.add_argument("-p", "--pack",action="store_true", default=False, help="repack and sign the rpk by haptoolkit.")
    parser.add_argument("-f", "--feature",action="store_true", default=False, help="scan features in rpk")
    args = parser.parse_args()

    rootDir = args.path
    # exchange path to abspath
    rootDir = os.path.abspath(rootDir)
    jsdir = args.js
    debug = args.debug
    pack = args.pack
    feat = args.feature
    default = True

    if jsdir:
        if not Rpktool.reformat_files(rootDir, 'js'):
            return
        print('')
        log.info("All Done. Reformat js to "+ Fore.CYAN+ rootDir)
        return
    if feat:
        nowTime = datetime.datetime.now().strftime(r'%Y-%m-%d-%H-%M-%S')
        if os.path.isdir(rootDir):
            rpk_count = 0
            report_file = rootDir+"/features_scan_report_"+nowTime+".txt"
            report = Report(report_file)
            for rt, dirs, files, in os.walk(rootDir):
                for fr in files:
                    if fr.endswith('.rpk'):
                        rpk_count += 1
                        rpktool = Rpktool(file_path=os.path.join(rt, fr), file_type='js',del_flag=True)
                        if not rpktool.extract_rpk():
                            return
                        result = rpktool.print_rpk_info(True)
                        report.write_report(result)
                        rpktool.print_features(report)
                        report.write_report('\n')
                        print('\n')
            if rpk_count > 0:
                log.info("Scanning rpks success! Report is :"+Fore.CYAN+ report_file)
            else:
                log.error(".rpk file not found!")
        elif os.path.isfile(rootDir):
            report_file = os.path.dirname(rootDir)+"/features_scan_report_"+nowTime+".txt"
            report = Report(report_file)
            if rootDir.endswith('.rpk'):
                rpktool = Rpktool(file_path=rootDir, file_type='js',del_flag=True)
                if not rpktool.extract_rpk():
                    return
                result = rpktool.print_rpk_info(True)
                report.write_report(result)
                rpktool.print_features(report)
                log.info("Scanning rpks success! Report is :"+Fore.CYAN+ report_file)
            else:
                log.error(".rpk file not found!")
        del report
        return
    #init rpktool
    if pack:
        # stop to unpack
        default = False
        rpktool = Rpktool(file_path=rootDir, file_type='js')
        if not rpktool.pack_rpk():
            return
        log.info("Packing rpk success! New rpk is :"+Fore.CYAN+ os.path.abspath(rpktool.pack_output))
        if debug:
            rootDir = rpktool.pack_output
        else:
            return
    if debug:
        rpktool =Rpktool(file_path=rootDir, file_type='js', del_flag=True)
        if not rpktool.extract_rpk():
            return
        result = rpktool.print_rpk_info()
        # start debug rpk
        log.verbose("Start to debug rpk. Ctrl-C to exit.")
        rpktool.debug_rpk()
        return
    # unpack a rpk
    if default:    
        rpktool = Rpktool(file_path=rootDir, file_type='js')
        if not rpktool.process_rpk():
            return
        print('')
        log.info("All Done. Extracted RPK to "+ Fore.CYAN+ rpktool.output_path)
        result = rpktool.print_rpk_info()

def debug():
    rpktool =Rpktool(file_path="/Users/80241260/Documents/Audit/2020/govaffairs2/org.hap.govaffairs.debug.rpk", file_type='js')
    if not rpktool.process_rpk():
        return
    result = rpktool.print_rpk_info()
    # start debug rpk
    log = Print(True)


if __name__ == "__main__":
    main()
    #debug()