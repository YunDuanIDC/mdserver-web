# coding:utf-8

import sys
import io
import os
import time
import re
import json
import shutil


sys.path.append(os.getcwd() + "/class/core")
import mw

if mw.isAppleSystem():
    cmd = 'ls /usr/local/lib/ | grep python  | cut -d \\  -f 1 | awk \'END {print}\''
    info = mw.execShell(cmd)
    p = "/usr/local/lib/" + info[0].strip() + "/site-packages"
    sys.path.append(p)

app_debug = False
if mw.isAppleSystem():
    app_debug = True


def getPluginName():
    return 'php-apt'


def getServerDir():
    return '/etc/php'


def getPluginDir():
    return mw.getPluginDir() + '/' + getPluginName()


def getArgs():
    args = sys.argv[3:]
    tmp = {}
    args_len = len(args)

    if args_len == 1:
        t = args[0].strip('{').strip('}')
        t = t.split(':')
        tmp[t[0]] = t[1]
    elif args_len > 1:
        for i in range(len(args)):
            t = args[i].split(':')
            tmp[t[0]] = t[1]

    return tmp


def checkArgs(data, ck=[]):
    for i in range(len(ck)):
        if not ck[i] in data:
            return (False, mw.returnJson(False, '参数:(' + ck[i] + ')没有!'))
    return (True, mw.returnJson(True, 'ok'))


def getConf(version):
    path = getServerDir() + '/' + version + '/fpm/php.ini'
    return path


def getFpmConfFile(version):
    return getServerDir() + '/php/' + version + '/fpm/pool.d/mw.conf'


def status(version):
    # ps -ef|grep 'php/81' |grep -v grep | grep -v python | awk '{print $2}
    cmd = "ps -ef|grep 'php/" + version + \
        "' |grep -v grep | grep -v python | awk '{print $2}'"
    data = mw.execShell(cmd)
    if data[0] == '':
        return 'stop'
    return 'start'


def contentReplace(content, version):
    service_path = mw.getServerDir()
    content = content.replace('{$ROOT_PATH}', mw.getRootDir())
    content = content.replace('{$SERVER_PATH}', service_path)
    content = content.replace('{$PHP_VERSION}', version)
    content = content.replace('{$LOCAL_IP}', mw.getLocalIp())

    if mw.isAppleSystem():
        # user = mw.execShell(
        #     "who | sed -n '2, 1p' |awk '{print $1}'")[0].strip()
        content = content.replace('{$PHP_USER}', 'nobody')
        content = content.replace('{$PHP_GROUP}', 'nobody')

        rep = 'listen.owner\s*=\s*(.+)\r?\n'
        val = ';listen.owner = nobody\n'
        content = re.sub(rep, val, content)

        rep = 'listen.group\s*=\s*(.+)\r?\n'
        val = ';listen.group = nobody\n'
        content = re.sub(rep, val, content)

        rep = 'user\s*=\s*(.+)\r?\n'
        val = ';user = nobody\n'
        content = re.sub(rep, val, content)

        rep = r'[^\.]group\s*=\s*(.+)\r?\n'
        val = ';group = nobody\n'
        content = re.sub(rep, val, content)

    else:
        content = content.replace('{$PHP_USER}', 'www')
        content = content.replace('{$PHP_GROUP}', 'www')
    return content


def makeOpenrestyConf(version):

    sdir = mw.getServerDir()
    d_pathinfo = sdir + '/web_conf/php/pathinfo.conf'
    if not os.path.exists(d_pathinfo):
        s_pathinfo = getPluginDir() + '/conf/pathinfo.conf'
        shutil.copyfile(s_pathinfo, d_pathinfo)

    dst_dir = sdir + '/web_conf/php'
    dst_dir_conf = sdir + '/web_conf/php/conf'
    dst_dir_status = sdir + '/web_conf/php/status'
    if not os.path.exists(dst_dir):
        mw.execShell('mkdir -p ' + dst_dir)

    if not os.path.exists(dst_dir_conf):
        mw.execShell('mkdir -p ' + dst_dir_conf)

    if not os.path.exists(dst_dir_status):
        mw.execShell('mkdir -p ' + dst_dir_status)

    info = getPluginDir() + '/info.json'
    content = mw.readFile(info)
    content = json.loads(content)
    versions = content['versions']
    tpl = getPluginDir() + '/conf/enable-php.conf'
    tpl_content = mw.readFile(tpl)
    dfile = sdir + '/web_conf/php/conf/enable-php-apt' + version + '.conf'
    if not os.path.exists(dfile):
        w_content = contentReplace(tpl_content, version)
        mw.writeFile(dfile, w_content)

    # php-fpm status
    dfile = sdir + '/web_conf/php/status/phpfpm_status_apt' + version + '.conf'
    tpl = getPluginDir() + '/conf/phpfpm_status.conf'
    if not os.path.exists(dfile):
        content = mw.readFile(tpl)
        content = contentReplace(content, version)
        mw.writeFile(dfile, content)


def phpFpmWwwReplace(version):
    service_php_fpm_dir = getServerDir() + '/' + version + '/fpm/pool.d'
    if not os.path.exists(service_php_fpm_dir):
        os.mkdir(service_php_fpm_dir)

    service_php_fpmwww = service_php_fpm_dir + '/www.conf'
    if os.path.exists(service_php_fpmwww):
        # 原来文件备份
        mw.execShell('mv ' + service_php_fpmwww +
                     ' ' + service_php_fpmwww + '.bak')

    service_php_fpm_mw = service_php_fpm_dir + '/mw.conf'
    if not os.path.exists(service_php_fpm_mw):
        tpl_php_fpmwww = getPluginDir() + '/conf/www.conf'
        content = mw.readFile(tpl_php_fpmwww)
        content = contentReplace(content, version)
        mw.writeFile(service_php_fpm_mw, content)


def deleteConfList(version):
    sdir = mw.getServerDir()
    enable_conf = sdir + '/web_conf/php/conf/enable-php-apt' + version + '.conf'
    status_conf = sdir + '/web_conf/php/status/phpfpm_status_apt' + version + '.conf'

    clist = (status_conf, enable_conf)
    for f in clist:
        if os.path.exists(f):
            os.remove(f)


def initReplace(version):
    makeOpenrestyConf(version)
    phpFpmWwwReplace(version)

    # systemd
    # mw.execShell('systemctl daemon-reload')
    return 'ok'


def phpOp(version, method):
    if method == 'start':
        initReplace(version)

    if mw.isAppleSystem():
        return 'fail'
    data = mw.execShell('systemctl ' + method + ' ' +
                        'php' + version + '-php-fpm')
    if data[1] == '':
        return 'ok'
    return data[1]


def start(version):
    return phpOp(version, 'start')


def stop(version):
    status = phpOp(version, 'stop')
    deleteConfList(version)
    return status


def restart(version):
    return phpOp(version, 'restart')


def reload(version):
    return phpOp(version, 'reload')


def initdStatus(version):
    if mw.isAppleSystem():
        return "Apple Computer does not support"

    shell_cmd = 'systemctl status php' + version + \
        '-fpm | grep loaded | grep "enabled;"'
    data = mw.execShell(shell_cmd)
    if data[0] == '':
        return 'fail'
    return 'ok'


def initdInstall(version):
    if mw.isAppleSystem():
        return "Apple Computer does not support"

    mw.execShell('systemctl enable php' + version + '-fpm')
    return 'ok'


def initdUinstall(version):
    if mw.isAppleSystem():
        return "Apple Computer does not support"

    mw.execShell('systemctl disable php' + version + '-fpm')
    return 'ok'


def fpmLog(version):
    return '/var/opt/remi/php' + version + '/log/php-fpm/error.log'


def fpmSlowLog(version):
    return '/var/opt/remi/php' + version + '/log/php-fpm/www-slow.log'


def getPhpConf(version):
    gets = [
        {'name': 'short_open_tag', 'type': 1, 'ps': '短标签支持'},
        {'name': 'asp_tags', 'type': 1, 'ps': 'ASP标签支持'},
        {'name': 'max_execution_time', 'type': 2, 'ps': '最大脚本运行时间'},
        {'name': 'max_input_time', 'type': 2, 'ps': '最大输入时间'},
        {'name': 'max_input_vars', 'type': 2, 'ps': '最大输入数量'},
        {'name': 'memory_limit', 'type': 2, 'ps': '脚本内存限制'},
        {'name': 'post_max_size', 'type': 2, 'ps': 'POST数据最大尺寸'},
        {'name': 'file_uploads', 'type': 1, 'ps': '是否允许上传文件'},
        {'name': 'upload_max_filesize', 'type': 2, 'ps': '允许上传文件的最大尺寸'},
        {'name': 'max_file_uploads', 'type': 2, 'ps': '允许同时上传文件的最大数量'},
        {'name': 'default_socket_timeout', 'type': 2, 'ps': 'Socket超时时间'},
        {'name': 'error_reporting', 'type': 3, 'ps': '错误级别'},
        {'name': 'display_errors', 'type': 1, 'ps': '是否输出详细错误信息'},
        {'name': 'cgi.fix_pathinfo', 'type': 0, 'ps': '是否开启pathinfo'},
        {'name': 'date.timezone', 'type': 3, 'ps': '时区'}
    ]
    phpini = mw.readFile(getConf(version))
    result = []
    for g in gets:
        rep = g['name'] + '\s*=\s*([0-9A-Za-z_& ~]+)(\s*;?|\r?\n)'
        tmp = re.search(rep, phpini)
        if not tmp:
            continue
        g['value'] = tmp.groups()[0]
        result.append(g)
    return mw.getJson(result)


def submitPhpConf(version):
    gets = ['display_errors', 'cgi.fix_pathinfo', 'date.timezone', 'short_open_tag',
            'asp_tags', 'max_execution_time', 'max_input_time', 'max_input_vars', 'memory_limit',
            'post_max_size', 'file_uploads', 'upload_max_filesize', 'max_file_uploads',
            'default_socket_timeout', 'error_reporting']
    args = getArgs()
    filename = getConf(version)
    phpini = mw.readFile(filename)
    for g in gets:
        if g in args:
            rep = g + '\s*=\s*(.+)\r?\n'
            val = g + ' = ' + args[g] + '\n'
            phpini = re.sub(rep, val, phpini)
    mw.writeFile(filename, phpini)
    reload(version)
    return mw.returnJson(True, '设置成功')


def getLimitConf(version):
    fileini = getConf(version)
    phpini = mw.readFile(fileini)
    filefpm = getFpmConfFile(version)
    phpfpm = mw.readFile(filefpm)

    # print fileini, filefpm
    data = {}
    try:
        rep = "upload_max_filesize\s*=\s*([0-9]+)M"
        tmp = re.search(rep, phpini).groups()
        data['max'] = tmp[0]
    except:
        data['max'] = '50'

    try:
        rep = "request_terminate_timeout\s*=\s*([0-9]+)\n"
        tmp = re.search(rep, phpfpm).groups()
        data['maxTime'] = tmp[0]
    except:
        data['maxTime'] = 0

    try:
        rep = r"\n;*\s*cgi\.fix_pathinfo\s*=\s*([0-9]+)\s*\n"
        tmp = re.search(rep, phpini).groups()

        if tmp[0] == '1':
            data['pathinfo'] = True
        else:
            data['pathinfo'] = False
    except:
        data['pathinfo'] = False

    return mw.getJson(data)


def setMaxTime(version):
    args = getArgs()
    data = checkArgs(args, ['time'])
    if not data[0]:
        return data[1]

    time = args['time']
    if int(time) < 30 or int(time) > 86400:
        return mw.returnJson(False, '请填写30-86400间的值!')

    filefpm = getFpmConfFile(version)
    conf = mw.readFile(filefpm)
    rep = "request_terminate_timeout\s*=\s*([0-9]+)\n"
    conf = re.sub(rep, "request_terminate_timeout = " + time + "\n", conf)
    mw.writeFile(filefpm, conf)

    fileini = getConf(version)
    phpini = mw.readFile(fileini)
    rep = "max_execution_time\s*=\s*([0-9]+)\r?\n"
    phpini = re.sub(rep, "max_execution_time = " + time + "\n", phpini)
    rep = "max_input_time\s*=\s*([0-9]+)\r?\n"
    phpini = re.sub(rep, "max_input_time = " + time + "\n", phpini)
    mw.writeFile(fileini, phpini)
    return mw.returnJson(True, '设置成功!')


def setMaxSize(version):
    args = getArgs()
    data = checkArgs(args, ['max'])
    if not data[0]:
        return data[1]

    maxVal = args['max']
    if int(maxVal) < 2:
        return mw.returnJson(False, '上传大小限制不能小于2MB!')

    path = getConf(version)
    conf = mw.readFile(path)
    rep = u"\nupload_max_filesize\s*=\s*[0-9]+M"
    conf = re.sub(rep, u'\nupload_max_filesize = ' + maxVal + 'M', conf)
    rep = u"\npost_max_size\s*=\s*[0-9]+M"
    conf = re.sub(rep, u'\npost_max_size = ' + maxVal + 'M', conf)
    mw.writeFile(path, conf)

    msg = mw.getInfo('设置PHP-{1}最大上传大小为[{2}MB]!', (version, maxVal,))
    mw.writeLog('插件管理[PHP]', msg)
    return mw.returnJson(True, '设置成功!')


def getFpmConfig(version):

    filefpm = getFpmConfFile(version)
    conf = mw.readFile(filefpm)
    data = {}
    rep = "\s*pm.max_children\s*=\s*([0-9]+)\s*"
    tmp = re.search(rep, conf).groups()
    data['max_children'] = tmp[0]

    rep = "\s*pm.start_servers\s*=\s*([0-9]+)\s*"
    tmp = re.search(rep, conf).groups()
    data['start_servers'] = tmp[0]

    rep = "\s*pm.min_spare_servers\s*=\s*([0-9]+)\s*"
    tmp = re.search(rep, conf).groups()
    data['min_spare_servers'] = tmp[0]

    rep = "\s*pm.max_spare_servers \s*=\s*([0-9]+)\s*"
    tmp = re.search(rep, conf).groups()
    data['max_spare_servers'] = tmp[0]

    rep = "\s*pm\s*=\s*(\w+)\s*"
    tmp = re.search(rep, conf).groups()
    data['pm'] = tmp[0]
    return mw.getJson(data)


def setFpmConfig(version):
    args = getArgs()
    # if not 'max' in args:
    #     return 'missing time args!'

    version = args['version']
    max_children = args['max_children']
    start_servers = args['start_servers']
    min_spare_servers = args['min_spare_servers']
    max_spare_servers = args['max_spare_servers']
    pm = args['pm']

    file = getServerDir() + '/php' + version + '/php-fpm.d/www.conf'
    conf = mw.readFile(file)

    rep = "\s*pm.max_children\s*=\s*([0-9]+)\s*"
    conf = re.sub(rep, "\npm.max_children = " + max_children, conf)

    rep = "\s*pm.start_servers\s*=\s*([0-9]+)\s*"
    conf = re.sub(rep, "\npm.start_servers = " + start_servers, conf)

    rep = "\s*pm.min_spare_servers\s*=\s*([0-9]+)\s*"
    conf = re.sub(rep, "\npm.min_spare_servers = " +
                  min_spare_servers, conf)

    rep = "\s*pm.max_spare_servers \s*=\s*([0-9]+)\s*"
    conf = re.sub(rep, "\npm.max_spare_servers = " +
                  max_spare_servers + "\n", conf)

    rep = "\s*pm\s*=\s*(\w+)\s*"
    conf = re.sub(rep, "\npm = " + pm + "\n", conf)

    mw.writeFile(file, conf)
    reload(version)

    msg = mw.getInfo('设置PHP-{1}并发设置,max_children={2},start_servers={3},min_spare_servers={4},max_spare_servers={5}', (version, max_children,
                                                                                                                      start_servers, min_spare_servers, max_spare_servers,))
    mw.writeLog('插件管理[PHP]', msg)
    return mw.returnJson(True, '设置成功!')


def checkFpmStatusFile(version):
    if not mw.isInstalledWeb():
        return False

    dfile = getServerDir() + '/nginx/conf/php_status/phpfpm_status_yum' + version + '.conf'
    if not os.path.exists(dfile):
        tpl = getPluginDir() + '/conf/phpfpm_status.conf'
        content = mw.readFile(tpl)
        content = contentReplace(content, version)
        mw.writeFile(dfile, content)
        mw.restartWeb()
    return True


def getFpmStatus(version):

    checkFpmStatusFile(version)
    stat = status(version)
    if stat == 'stop':
        return mw.returnJson(False, 'PHP[' + version + ']未启动!!!')

    try:
        url = 'http://' + mw.getHostAddr() + '/phpfpm_status_yum' + version + '?json'
        result = mw.httpGet(url, 1)
        data = json.loads(result)
        fTime = time.localtime(int(data['start time']))
        data['start time'] = time.strftime('%Y-%m-%d %H:%M:%S', fTime)
    except Exception as e:
        url = 'http://127.0.0.1/phpfpm_status_yum' + version + '?json'
        result = mw.httpGet(url, 1)
        data = json.loads(result)
        fTime = time.localtime(int(data['start time']))
        data['start time'] = time.strftime('%Y-%m-%d %H:%M:%S', fTime)
    except Exception as e:
        data = {}

    return mw.returnJson(True, "OK", data)


def getDisableFunc(version):
    filename = getConf(version)
    if not os.path.exists(filename):
        return mw.returnJson(False, '指定PHP版本不存在!')

    phpini = mw.readFile(filename)
    data = {}
    rep = "disable_functions\s*=\s{0,1}(.*)\n"
    tmp = re.search(rep, phpini).groups()
    data['disable_functions'] = tmp[0]
    return mw.getJson(data)


def setDisableFunc(version):
    filename = getConf(version)
    if not os.path.exists(filename):
        return mw.returnJson(False, '指定PHP版本不存在!')

    args = getArgs()
    disable_functions = args['disable_functions']

    phpini = mw.readFile(filename)
    rep = "disable_functions\s*=\s*.*\n"
    phpini = re.sub(rep, 'disable_functions = ' +
                    disable_functions + "\n", phpini)

    msg = mw.getInfo('修改PHP-{1}的禁用函数为[{2}]', (version, disable_functions,))
    mw.writeLog('插件管理[PHP-YUM]', msg)
    mw.writeFile(filename, phpini)
    reload(version)
    return mw.returnJson(True, '设置成功!')


def checkPhpinfoFile(v):
    sdir = mw.getServerDir()
    dfile = sdir + '/web_conf/php/status/phpinfo_' + v + '.conf'
    tpl = getPluginDir() + '/conf/phpinfo.conf'
    content = mw.readFile(tpl)
    content = contentReplace(content, v)
    mw.writeFile(dfile, content)
    mw.restartWeb()


def getPhpinfo(v):
    checkPhpinfoFile(v)
    sPath = mw.getRootDir() + '/phpinfo/' + v

    mw.execShell("rm -rf " + mw.getRootDir() + '/phpinfo')
    mw.execShell("mkdir -p " + sPath)
    mw.writeFile(sPath + '/phpinfo.php', '<?php phpinfo(); ?>')
    url = 'http://127.0.0.1/' + v + '/phpinfo.php'
    phpinfo = mw.httpGet(url)
    os.system("rm -rf " + mw.getRootDir() + '/phpinfo')
    return phpinfo


def get_php_info(args):
    if not mw.isInstalledWeb():
        return "openresty is not running!!!"
    return getPhpinfo(args['version'])


def getLibConf(version):
    fname = getConf(version)
    if not os.path.exists(fname):
        return mw.returnJson(False, '指定PHP版本不存在!')

    # phpini = mw.readFile(fname)
    content = mw.execShell(
        'cat /etc/php/' + version + '/fpm/conf.d/*' + " | grep -v '^;' |tr -s '\n'")
    content = content[0]

    libpath = getPluginDir() + '/versions/phplib.conf'
    phplib = json.loads(mw.readFile(libpath))

    libs = []
    tasks = mw.M('tasks').where(
        "status!=?", ('1',)).field('status,name').select()
    for lib in phplib:
        lib['task'] = '1'
        for task in tasks:
            tmp = mw.getStrBetween('[', ']', task['name'])
            if not tmp:
                continue
            tmp1 = tmp.split('-')
            if tmp1[0].lower() == lib['name'].lower():
                lib['task'] = task['status']
                lib['phpversions'] = []
                lib['phpversions'].append(tmp1[1])
        if content.find(lib['check']) == -1:
            lib['status'] = False
        else:
            lib['status'] = True
        libs.append(lib)
    return mw.returnJson(True, 'OK!', libs)


def installLib(version):
    args = getArgs()
    data = checkArgs(args, ['name'])
    if not data[0]:
        return data[1]

    name = args['name']
    execstr = "cd " + getPluginDir() + '/versions/' + \
        " && /bin/bash common.sh " + version + ' install ' + name

    rettime = time.strftime('%Y-%m-%d %H:%M:%S')
    insert_info = (None, '安装PHPAPT[' + name + '-' + version + ']',
                   'execshell', '0', rettime, execstr)
    mw.M('tasks').add('id,name,type,status,addtime,execstr', insert_info)

    mw.triggerTask()
    return mw.returnJson(True, '已将下载任务添加到队列!')


def uninstallLib(version):
    args = getArgs()
    data = checkArgs(args, ['name'])
    if not data[0]:
        return data[1]

    name = args['name']
    execstr = "cd " + getPluginDir() + '/versions/' + \
        " && /bin/bash common.sh " + version + ' uninstall ' + name

    data = mw.execShell(execstr)
    # data[0] == '' and
    if data[1] == '':
        return mw.returnJson(True, '已经卸载成功!')
    else:
        return mw.returnJson(False, '卸载错误信息!:' + data[1])


def installPreInspection(version):
    sys = mw.execShell(
        "cat /etc/*-release | grep PRETTY_NAME |awk -F = '{print $2}' | awk -F '\"' '{print $2}'| awk '{print $1}'")

    sys_id = mw.execShell(
        "cat /etc/*-release | grep VERSION_ID | awk -F = '{print $2}' | awk -F '\"' '{print $2}'")

    sysName = sys[0].strip().lower()
    sysId = sys_id[0].strip()

    if not sysName in ('debian', 'ubuntu'):
        return '暂时支持debian,ubuntu'
    return 'ok'

if __name__ == "__main__":

    if len(sys.argv) < 3:
        print('missing parameters')
        exit(0)

    func = sys.argv[1]

    inputVer = sys.argv[2]
    version = inputVer[0] + '.' + inputVer[1]

    if func == 'status':
        print(status(version))
    elif func == 'start':
        print(start(version))
    elif func == 'stop':
        print(stop(version))
    elif func == 'restart':
        print(restart(version))
    elif func == 'reload':
        print(reload(version))
    elif func == 'install_pre_inspection':
        print(installPreInspection(version))
    elif func == 'initd_status':
        print(initdStatus(version))
    elif func == 'initd_install':
        print(initdInstall(version))
    elif func == 'initd_uninstall':
        print(initdUinstall(version))
    elif func == 'fpm_log':
        print(fpmLog(version))
    elif func == 'fpm_slow_log':
        print(fpmSlowLog(version))
    elif func == 'conf':
        print(getConf(version))
    elif func == 'get_php_conf':
        print(getPhpConf(version))
    elif func == 'get_fpm_conf_file':
        print(getFpmConfFile(version))
    elif func == 'submit_php_conf':
        print(submitPhpConf(version))
    elif func == 'get_limit_conf':
        print(getLimitConf(version))
    elif func == 'set_max_time':
        print(setMaxTime(version))
    elif func == 'set_max_size':
        print(setMaxSize(version))
    elif func == 'get_fpm_conf':
        print(getFpmConfig(version))
    elif func == 'set_fpm_conf':
        print(setFpmConfig(version))
    elif func == 'get_fpm_status':
        print(getFpmStatus(version))
    elif func == 'get_disable_func':
        print(getDisableFunc(version))
    elif func == 'set_disable_func':
        print(setDisableFunc(version))
    elif func == 'get_phpinfo':
        print(getPhpinfo(version))
    elif func == 'get_lib_conf':
        print(getLibConf(version))
    elif func == 'install_lib':
        print(installLib(version))
    elif func == 'uninstall_lib':
        print(uninstallLib(version))
    else:
        print("fail")
