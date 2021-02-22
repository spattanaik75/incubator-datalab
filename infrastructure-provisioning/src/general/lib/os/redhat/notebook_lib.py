#!/usr/bin/python3

# *****************************************************************************
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#
# ******************************************************************************

import json
import os
import sys
from datalab.common_lib import manage_pkg
from datalab.fab import *
from datalab.notebook_lib import *
from fabric import *
from patchwork.files import exists


def enable_proxy(proxy_host, proxy_port):
    try:
        proxy_string = "http://%s:%s" % (proxy_host, proxy_port)
        conn.sudo('sed -i "/^export http_proxy/d" /etc/profile')
        conn.sudo('sed -i "/^export https_proxy/d" /etc/profile')
        conn.sudo('echo export http_proxy=' + proxy_string + ' >> /etc/profile')
        conn.sudo('echo export https_proxy=' + proxy_string + ' >> /etc/profile')
        if exists('/etc/yum.conf'):
            conn.sudo('sed -i "/^proxy=/d" /etc/yum.conf')
        conn.sudo("echo 'proxy={}' >> /etc/yum.conf".format(proxy_string))
        manage_pkg('clean all', 'remote', '')
    except:
        sys.exit(1)


def downgrade_python_version():
    try:
       conn.sudo('python3 -c "import os,sys,yum; yb = yum.YumBase(); pl = yb.doPackageLists(); \
        version = [pkg.vr for pkg in pl.installed if pkg.name == \'python\']; \
        os.system(\'yum -y downgrade python python-devel-2.7.5-58.el7.x86_64 python-libs-2.7.5-58.el7.x86_64\') \
        if version != [] and version[0] == \'2.7.5-68.el7\' else False"')
    except:
        sys.exit(1)


def ensure_r_local_kernel(spark_version, os_user, templates_dir, kernels_dir):
    if not exists(conn,'/home/{}/.ensure_dir/r_kernel_ensured'.format(os_user)):
        try:
            conn.sudo('chown -R ' + os_user + ':' + os_user + ' /home/' + os_user + '/.local')
            conn.run('R -e "IRkernel::installspec()"')
            conn.sudo('ln -s /opt/spark/ /usr/local/spark')
            try:
                conn.sudo('cd /usr/local/spark/R/lib/SparkR; R -e "install.packages(\'roxygen2\',repos=\'https://cloud.r-project.org\')" R -e "devtools::check(\'.\')"')
            except:
                pass
            conn.sudo('cd /usr/local/spark/R/lib/SparkR; R -e "devtools::install(\'.\')"')
            r_version = conn.sudo("R --version | awk '/version / {print $3}'").stdout
            conn.put(templates_dir + 'r_template.json', '/tmp/r_template.json')
            conn.sudo('sed -i "s|R_VER|' + r_version + '|g" /tmp/r_template.json')
            conn.sudo('sed -i "s|SP_VER|' + spark_version + '|g" /tmp/r_template.json')
            conn.sudo('\cp -f /tmp/r_template.json {}/ir/kernel.json'.format(kernels_dir))
            conn.sudo('ln -s /usr/lib64/R/ /usr/lib/R')
            conn.sudo('chown -R ' + os_user + ':' + os_user + ' /home/' + os_user + '/.local')
            conn.sudo('touch /home/{}/.ensure_dir/r_kernel_ensured'.format(os_user))
        except:
            sys.exit(1)


def ensure_r(os_user, r_libs, region, r_mirror):
    if not exists(conn,'/home/{}/.ensure_dir/r_ensured'.format(os_user)):
        try:
            if region == 'cn-north-1':
                r_repository = r_mirror
            else:
                r_repository = 'https://cloud.r-project.org'
            manage_pkg('-y install', 'remote', 'cmake')
            manage_pkg('-y install', 'remote', 'libcur*')
            conn.sudo('echo -e "[base]\nname=CentOS-7-Base\nbaseurl=http://buildlogs.centos.org/centos/7/os/x86_64-20140704-1/\ngpgcheck=1\ngpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-CentOS-7\npriority=1\nexclude=php mysql" >> /etc/yum.repos.d/CentOS-base.repo')
            manage_pkg('-y install', 'remote', 'R R-core R-core-devel R-devel --nogpgcheck')
            conn.sudo('R CMD javareconf')
            conn.sudo('cd /root; git clone https://github.com/zeromq/zeromq4-x.git; cd zeromq4-x/; mkdir build; cd build; cmake ..; make install; ldconfig')
            for i in r_libs:
                conn.sudo('R -e "install.packages(\'{}\',repos=\'{}\')"'.format(i, r_repository))
            conn.sudo('R -e "library(\'devtools\');install.packages(repos=\'{}\',c(\'rzmq\',\'repr\',\'digest\',\'stringr\',\'RJSONIO\',\'functional\',\'plyr\'))"'.format(r_repository))
            conn.sudo('R -e "library(\'devtools\');install_github(\'IRkernel/repr\');install_github(\'IRkernel/IRdisplay\');install_github(\'IRkernel/IRkernel\');"')
            conn.sudo('R -e "library(\'devtools\');install_version(\'keras\', version = \'{}\', repos = \'{}\');"'.format(os.environ['notebook_keras_version'],r_repository))
            conn.sudo('R -e "install.packages(\'RJDBC\',repos=\'{}\',dep=TRUE)"'.format(r_repository))
            conn.sudo('touch /home/{}/.ensure_dir/r_ensured'.format(os_user))
        except:
            sys.exit(1)


def install_rstudio(os_user, local_spark_path, rstudio_pass, rstudio_version):
    if not exists(conn,'/home/' + os_user + '/.ensure_dir/rstudio_ensured'):
        try:
            manage_pkg('-y install --nogpgcheck', 'remote', 'https://download2.rstudio.org/server/centos6/x86_64/rstudio-server-rhel-{}-x86_64.rpm'.format(rstudio_version))
            conn.sudo('mkdir -p /mnt/var')
            conn.sudo('chown {0}:{0} /mnt/var'.format(os_user))
            conn.sudo("sed -i '/Type=forking/a \Environment=USER=datalab-user' /lib/systemd/system/rstudio-server.service")
            conn.sudo(
                "sed -i '/ExecStart/s|=/usr/lib/rstudio-server/bin/rserver|=/bin/bash -c \"export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/opt/cudnn/lib64:/usr/local/cuda/lib64; /usr/lib/rstudio-server/bin/rserver --auth-none 1|g' /lib/systemd/system/rstudio-server.service")
            conn.sudo("sed -i '/ExecStart/s|$|\"|g' /lib/systemd/system/rstudio-server.service")
            conn.sudo("systemctl daemon-reload")
            conn.sudo('touch /home/{}/.Renviron'.format(os_user))
            conn.sudo('chown {0}:{0} /home/{0}/.Renviron'.format(os_user))
            conn.sudo('''echo 'SPARK_HOME="{0}"' >> /home/{1}/.Renviron'''.format(local_spark_path, os_user))
            conn.sudo('touch /home/{}/.Rprofile'.format(os_user))
            conn.sudo('chown {0}:{0} /home/{0}/.Rprofile'.format(os_user))
            conn.sudo('''echo 'library(SparkR, lib.loc = c(file.path(Sys.getenv("SPARK_HOME"), "R", "lib")))' >> /home/{}/.Rprofile'''.format(os_user))
            http_proxy = conn.run('echo $http_proxy').stdout
            https_proxy = conn.run('echo $https_proxy').stdout
            conn.sudo('''echo 'Sys.setenv(http_proxy = \"{}\")' >> /home/{}/.Rprofile'''.format(http_proxy, os_user))
            conn.sudo('''echo 'Sys.setenv(https_proxy = \"{}\")' >> /home/{}/.Rprofile'''.format(https_proxy, os_user))
            conn.sudo('rstudio-server start')
            conn.sudo('echo "{0}:{1}" | chpasswd'.format(os_user, rstudio_pass))
            conn.sudo("sed -i '/exit 0/d' /etc/rc.local")
            conn.sudo('''bash -c "echo \'sed -i 's/^#SPARK_HOME/SPARK_HOME/' /home/{}/.Renviron\' >> /etc/rc.local"'''.format(os_user))
            conn.sudo("bash -c 'echo exit 0 >> /etc/rc.local'")
            conn.sudo('touch /home/{}/.ensure_dir/rstudio_ensured'.format(os_user))
        except:
            sys.exit(1)
    else:
        try:
            conn.sudo('echo "{0}:{1}" | chpasswd'.format(os_user, rstudio_pass))
        except:
            sys.exit(1)


def ensure_matplot(os_user):
    if not exists(conn,'/home/{}/.ensure_dir/matplot_ensured'.format(os_user)):
        try:
            conn.sudo('python3.5 -m pip install matplotlib==2.0.2 --no-cache-dir')
            if os.environ['application'] in ('tensor', 'deeplearning'):
                conn.sudo('python3.8 -m pip install -U numpy=={} --no-cache-dir'.format(os.environ['notebook_numpy_version']))
            conn.sudo('touch /home/{}/.ensure_dir/matplot_ensured'.format(os_user))
        except:
            sys.exit(1)


def ensure_sbt(os_user):
    if not exists(conn,'/home/{}/.ensure_dir/sbt_ensured'.format(os_user)):
        try:
            conn.sudo('curl https://bintray.com/sbt/rpm/rpm | sudo tee /etc/yum.repos.d/bintray-sbt-rpm.repo')
            manage_pkg('-y install', 'remote', 'sbt')
            conn.sudo('touch /home/{}/.ensure_dir/sbt_ensured'.format(os_user))
        except:
            sys.exit(1)


def ensure_jre_jdk(os_user):
    if not exists(conn,'/home/' + os_user + '/.ensure_dir/jre_jdk_ensured'):
        try:
            manage_pkg('-y install', 'remote', 'java-1.8.0-openjdk')
            manage_pkg('-y install', 'remote', 'java-1.8.0-openjdk-devel')
            conn.sudo('touch /home/' + os_user + '/.ensure_dir/jre_jdk_ensured')
        except:
            sys.exit(1)


def ensure_scala(scala_link, scala_version, os_user):
    if not exists(conn,'/home/' + os_user + '/.ensure_dir/scala_ensured'):
        try:
            conn.sudo('wget {}scala-{}.rpm -O /tmp/scala.rpm'.format(scala_link, scala_version))
            conn.sudo('rpm -i /tmp/scala.rpm')
            conn.sudo('touch /home/' + os_user + '/.ensure_dir/scala_ensured')
        except:
            sys.exit(1)


def ensure_additional_python_libs(os_user):
    if not exists(conn,'/home/' + os_user + '/.ensure_dir/additional_python_libs_ensured'):
        try:
            manage_pkg('clean', 'remote', 'all')
            manage_pkg('-y install', 'remote', 'zlib-devel libjpeg-turbo-devel --nogpgcheck')
            if os.environ['application'] in ('jupyter', 'zeppelin'):
                conn.sudo('python3.5 -m pip install NumPy=={} SciPy pandas Sympy Pillow sklearn --no-cache-dir'.format(os.environ['notebook_numpy_version']))
            if os.environ['application'] in ('tensor', 'deeplearning'):
                conn.sudo('python3.8 -m pip install opencv-python h5py --no-cache-dir')
            conn.sudo('touch /home/' + os_user + '/.ensure_dir/additional_python_libs_ensured')
        except:
            sys.exit(1)


def ensure_python3_specific_version(python3_version, os_user):
    if not exists(conn,'/home/' + os_user + '/.ensure_dir/python3_specific_version_ensured'):
        try:
            manage_pkg('-y install', 'remote', 'yum-utils python34 openssl-devel')
            manage_pkg('-y groupinstall', 'remote', 'development --nogpgcheck')
            if len(python3_version) < 4:
                python3_version = python3_version + ".0"
            conn.sudo('wget https://www.python.org/ftp/python/{0}/Python-{0}.tgz'.format(python3_version))
            conn.sudo('tar xzf Python-{0}.tgz; cd Python-{0}; ./configure --prefix=/usr/local; make altinstall'.format(python3_version))
            conn.sudo('touch /home/' + os_user + '/.ensure_dir/python3_specific_version_ensured')
        except:
            sys.exit(1)

def ensure_python3_libraries(os_user):
    if not exists(conn,'/home/' + os_user + '/.ensure_dir/python3_libraries_ensured'):
        try:
            manage_pkg('-y install', 'remote', 'https://centos7.iuscommunity.org/ius-release.rpm')
            manage_pkg('-y install', 'remote', 'python35u python35u-pip python35u-devel')
            conn.sudo('python3.5 -m pip install -U pip=={} setuptools --no-cache-dir'.format(os.environ['conf_pip_version']))
            conn.sudo('python3.5 -m pip install boto3 --no-cache-dir')
            conn.sudo('python3.5 -m pip install fabvenv fabric-virtualenv future --no-cache-dir')
            try:
                conn.sudo('python3.5 -m pip install tornado=={0} ipython==7.9.0 ipykernel=={1} --no-cache-dir' \
                     .format(os.environ['notebook_tornado_version'], os.environ['notebook_ipykernel_version']))
            except:
                conn.sudo('python3.5 -m pip install tornado=={0} ipython==5.0.0 ipykernel=={1} --no-cache-dir' \
                     .format(os.environ['notebook_tornado_version'], os.environ['notebook_ipykernel_version']))
            conn.sudo('touch /home/' + os_user + '/.ensure_dir/python3_libraries_ensured')
        except:
            sys.exit(1)


def install_tensor(os_user, cuda_version, cuda_file_name,
                   cudnn_version, cudnn_file_name, tensorflow_version,
                   templates_dir, nvidia_version):
    if not exists(conn,'/home/{}/.ensure_dir/tensor_ensured'.format(os_user)):
        try:
            # install nvidia drivers
            conn.sudo('echo "blacklist nouveau" >> /etc/modprobe.d/blacklist-nouveau.conf')
            conn.sudo('echo "options nouveau modeset=0" >> /etc/modprobe.d/blacklist-nouveau.conf')
            conn.sudo('dracut --force')
            with settings(warn_only=True):
                reboot(wait=150)
            manage_pkg('-y install', 'remote', 'libglvnd-opengl libglvnd-devel dkms gcc kernel-devel-$(uname -r) kernel-headers-$(uname -r)')
            conn.sudo('wget http://us.download.nvidia.com/XFree86/Linux-x86_64/{0}/NVIDIA-Linux-x86_64-{0}.run -O /home/{1}/NVIDIA-Linux-x86_64-{0}.run'.format(nvidia_version, os_user))
            conn.sudo('/bin/bash /home/{0}/NVIDIA-Linux-x86_64-{1}.run -s --dkms'.format(os_user, nvidia_version))
            conn.sudo('rm -f /home/{0}/NVIDIA-Linux-x86_64-{1}.run'.format(os_user, nvidia_version))
            # install cuda
            conn.sudo('python3.5 -m pip install --upgrade pip=={0} wheel numpy=={1} --no-cache-dir'. format(os.environ['conf_pip_version'], os.environ['notebook_numpy_version']))
            conn.sudo('wget -P /opt https://developer.nvidia.com/compute/cuda/{0}/prod/local_installers/{1}'.format(cuda_version, cuda_file_name))
            conn.sudo('sh /opt/{} --silent --toolkit'.format(cuda_file_name))
            conn.sudo('mv /usr/local/cuda-{} /opt/'.format(cuda_version))
            conn.sudo('ln -s /opt/cuda-{0} /usr/local/cuda-{0}'.format(cuda_version))
            conn.sudo('rm -f /opt/{}'.format(cuda_file_name))
            # install cuDNN
            conn.run('wget http://developer.download.nvidia.com/compute/redist/cudnn/v{0}/{1} -O /tmp/{1}'.format(cudnn_version, cudnn_file_name))
            conn.run('tar xvzf /tmp/{} -C /tmp'.format(cudnn_file_name))
            conn.sudo('mkdir -p /opt/cudnn/include')
            conn.sudo('mkdir -p /opt/cudnn/lib64')
            conn.sudo('mv /tmp/cuda/include/cudnn.h /opt/cudnn/include')
            conn.sudo('mv /tmp/cuda/lib64/libcudnn* /opt/cudnn/lib64')
            conn.sudo('chmod a+r /opt/cudnn/include/cudnn.h /opt/cudnn/lib64/libcudnn*')
            conn.run('echo "export LD_LIBRARY_PATH=\"$LD_LIBRARY_PATH:/opt/cudnn/lib64:/usr/local/cuda/lib64\"" >> ~/.bashrc')
            # install TensorFlow and run TensorBoard
            conn.sudo('wget https://storage.googleapis.com/tensorflow/linux/gpu/tensorflow_gpu-{}-cp27-none-linux_x86_64.whl'.format(tensorflow_version))
            conn.sudo('wget https://storage.googleapis.com/tensorflow/linux/gpu/tensorflow_gpu-{}-cp35-cp35m-linux_x86_64.whl'.format(tensorflow_version))
            conn.sudo('python3.8 -m pip install --upgrade tensorflow_gpu-{}-cp35-cp35m-linux_x86_64.whl --no-cache-dir'.format(tensorflow_version))
            conn.sudo('rm -rf /home/{}/tensorflow_gpu-*'.format(os_user))
            conn.sudo('mkdir /var/log/tensorboard; chown {0}:{0} -R /var/log/tensorboard'.format(os_user))
            conn.put('{}tensorboard.service'.format(templates_dir), '/tmp/tensorboard.service')
            conn.sudo("sed -i 's|OS_USR|{}|' /tmp/tensorboard.service".format(os_user))
            conn.sudo("chmod 644 /tmp/tensorboard.service")
            conn.sudo('\cp /tmp/tensorboard.service /etc/systemd/system/')
            conn.sudo("systemctl daemon-reload")
            conn.sudo("systemctl enable tensorboard")
            conn.sudo("systemctl start tensorboard")
            conn.sudo('touch /home/{}/.ensure_dir/tensor_ensured'.format(os_user))
        except:
            sys.exit(1)


def install_maven(os_user):
    if not exists(conn,'/home/' + os_user + '/.ensure_dir/maven_ensured'):
        conn.sudo('wget http://apache.volia.net/maven/maven-3/3.3.9/binaries/apache-maven-3.3.9-bin.tar.gz -O /tmp/maven.tar.gz')
        conn.sudo('tar -zxvf /tmp/maven.tar.gz -C /opt/')
        conn.sudo('ln -fs /opt/apache-maven-3.3.9/bin/mvn /usr/bin/mvn')
        conn.sudo('touch /home/' + os_user + '/.ensure_dir/maven_ensured')


def install_livy_dependencies(os_user):
    if not exists(conn,'/home/' + os_user + '/.ensure_dir/livy_dependencies_ensured'):
        conn.sudo('pip3.5 install cloudpickle requests requests-kerberos flake8 flaky pytest --no-cache-dir')
        conn.sudo('touch /home/' + os_user + '/.ensure_dir/livy_dependencies_ensured')


def install_maven_emr(os_user):
    if not os.path.exists('/home/' + os_user + '/.ensure_dir/maven_ensured'):
        subprocess.run('wget http://apache.volia.net/maven/maven-3/3.3.9/binaries/apache-maven-3.3.9-bin.tar.gz -O /tmp/maven.tar.gz', shell=True, check=True)
        subprocess.run('sudo tar -zxvf /tmp/maven.tar.gz -C /opt/', shell=True, check=True)
        subprocess.run('sudo ln -fs /opt/apache-maven-3.3.9/bin/mvn /usr/bin/mvn', shell=True, check=True)
        subprocess.run('touch /home/' + os_user + '/.ensure_dir/maven_ensured', shell=True, check=True)


def install_livy_dependencies_emr(os_user):
    if not os.path.exists('/home/' + os_user + '/.ensure_dir/livy_dependencies_ensured'):
        subprocess.run('sudo -i pip3.5 install cloudpickle requests requests-kerberos flake8 flaky pytest --no-cache-dir', shell=True, check=True)
        subprocess.run('touch /home/' + os_user + '/.ensure_dir/livy_dependencies_ensured', shell=True, check=True)


def install_nodejs(os_user):
    if not exists(conn,'/home/{}/.ensure_dir/nodejs_ensured'.format(os_user)):
        conn.sudo('curl -sL https://rpm.nodesource.com/setup_6.x | sudo -E bash -')
        manage_pkg('-y install', 'remote', 'nodejs')
        conn.sudo('touch /home/{}/.ensure_dir/nodejs_ensured'.format(os_user))


def install_os_pkg(requisites):
    status = list()
    error_parser = "Could not|No matching|Error:|failed|Requires:|Errno"
    new_pkgs_parser = "Dependency Installed:"
    try:
        print("Updating repositories and installing requested tools: {}".format(requisites))
        manage_pkg('update-minimal --security -y --skip-broken', 'remote', '')
        conn.sudo('export LC_ALL=C')
        for os_pkg in requisites:
            name, vers = os_pkg
            if vers != '' and vers !='N/A':
                version = vers
                os_pkg = "{}-{}".format(name, vers)
            else:
                version = 'N/A'
                os_pkg = name
            manage_pkg('-y install', 'remote', '{0} --nogpgcheck 2>&1 | tee /tmp/tee.tmp; if ! grep -w -E  "({1})" '
                                               '/tmp/tee.tmp >  /tmp/os_install_{2}.log; then  echo "" > /tmp/os_install_{2}.log;fi'.format(os_pkg, error_parser, name))
            install_output = conn.sudo('cat /tmp/tee.tmp').stdout
            err = conn.sudo('cat /tmp/os_install_{}.log'.format(name)).stdout.replace('"', "'")
            conn.sudo('cat /tmp/tee.tmp | if ! grep -w -E -A 30 "({1})" /tmp/tee.tmp > '
                 '/tmp/os_install_{0}.log; then echo "" > /tmp/os_install_{0}.log;fi'.format(name, new_pkgs_parser))
            dep = conn.sudo('cat /tmp/os_install_{}.log'.format(name)).stdout
            if dep == '':
                dep = []
            else:
                dep = dep[len(new_pkgs_parser): dep.find("Complete!") - 1].replace('  ', '').strip().split('\r\n')
                for n, i in enumerate(dep):
                    i = i.split('.')[0]
                    conn.sudo('yum info {0} 2>&1 | if ! grep Version > /tmp/os_install_{0}.log; then echo "" > /tmp/os_install_{0}.log;fi'.format(i))
                    dep[n] =sudo('cat /tmp/os_install_{}.log'.format(i)).replace('Version     : ', '{} v.'.format(i))
                dep = [i for i in dep if i]
            versions = []
            res = conn.sudo(
                'python3 -c "import os,sys,yum; yb = yum.YumBase(); pl = yb.doPackageLists(); print [pkg.vr for pkg in pl.installed if pkg.name == \'{0}\']"'.format(
                    name)).stdout.split('\r\n')[1]
            if err:
                status_msg = 'installation_error'
            elif res != []:
                version = res.split("'")[1].split("-")[0]
                status_msg = "installed"
            if 'No package {} available'.format(os_pkg) in install_output:
                versions = conn.sudo('yum --showduplicates list ' + name + ' | expand | grep ' + name + ' | awk \'{print $2}\'').stdout.replace('\r\n', '')
                if versions and versions != 'Error: No matching Packages to list':
                    versions = versions.split(' ')
                    status_msg = 'invalid_version'
                    for n, i in enumerate(versions):
                        if ':' in i:
                            versions[n] = i.split(':')[1].split('-')[0]
                        else:
                            versions[n] = i.split('-')[0]
                else:
                    versions = []
                    status_msg = 'invalid_name'
            status.append({"group": "os_pkg", "name": name, "version": version, "status": status_msg,
                           "error_message": err, "add_pkgs": dep, "available_versions": versions})
        return status
    except Exception as err:
        for os_pkg in requisites:
            name, vers = os_pkg
            status.append(
                {"group": "os_pkg", "name": name, "version": vers, "status": 'installation_error', "error_message": err})
        print("Failed to install OS packages: {}".format(requisites))
        return status

def remove_os_pkg(pkgs):
    try:
        manage_pkg('remove -y', 'remote', '{}'.format(' '.join(pkgs)))
    except:
        sys.exit(1)


def get_available_os_pkgs():
    try:
        manage_pkg('update-minimal --security -y --skip-broken', 'remote', '')
        downgrade_python_version()
        yum_raw = conn.sudo('python3 -c "import os,sys,yum; yb = yum.YumBase(); pl = yb.doPackageLists(); '
                            'print {pkg.name:pkg.vr for pkg in pl.available}"').stdout
        yum_re = re.sub\
            (r'\w*\s\w*\D\s\w*.\w*.\s\w*.\w*.\w.\w*.\w*.\w*', '', yum_raw)
        yum_list = yum_re.replace("'", "\"")
        os_pkgs = json.loads(yum_list)
        return os_pkgs
    except Exception as err:
        append_result("Failed to get available os packages.", str(err))
        sys.exit(1)


def install_opencv(os_user):
    if not exists(conn,'/home/{}/.ensure_dir/opencv_ensured'.format(os_user)):
        manage_pkg('-y install', 'remote', 'cmake python34 python34-devel python34-pip gcc gcc-c++')
        conn.sudo('pip3.4 install numpy=={} --no-cache-dir'.format(os.environ['notebook_numpy_version']))
        conn.sudo('pip3.5 install numpy=={} --no-cache-dir'.format(os.environ['notebook_numpy_version']))
        conn.run('git clone https://github.com/opencv/opencv.git')
        with conn.cd('/home/{}/opencv/'.format(os_user)):
            conn.run('git checkout 3.2.0')
            conn.run('mkdir release')
        with conn.cd('/home/{}/opencv/release/'.format(os_user)):
            conn.run('cmake -DINSTALL_TESTS=OFF -D CUDA_GENERATION=Auto -D CMAKE_BUILD_TYPE=RELEASE -D CMAKE_INSTALL_PREFIX=$(python2 -c "import sys; print(sys.prefix)") -D PYTHON_EXECUTABLE=$(which python2) ..')
            conn.run('make -j$(nproc)')
            conn.sudo('make install')
        conn.sudo('touch /home/' + os_user + '/.ensure_dir/opencv_ensured')


def install_caffe2(os_user, caffe2_version, cmake_version):
    if not exists(conn,'/home/{}/.ensure_dir/caffe2_ensured'.format(os_user)):
        env.shell = "/bin/bash -l -c -i"
        manage_pkg('update-minimal --security -y', 'remote', '')
        manage_pkg('-y install --nogpgcheck', 'remote', 'automake cmake3 gcc gcc-c++ kernel-devel leveldb-devel lmdb-devel libtool protobuf-devel graphviz')
        conn.sudo('pip3.5 install flask graphviz hypothesis jupyter matplotlib==2.0.2 numpy=={} protobuf pydot python-nvd3 pyyaml '
             'requests scikit-image scipy setuptools tornado future --no-cache-dir'.format(os.environ['notebook_numpy_version']))
        conn.sudo('cp /opt/cudnn/include/* /opt/cuda-8.0/include/')
        conn.sudo('cp /opt/cudnn/lib64/* /opt/cuda-8.0/lib64/')
        conn.sudo('wget https://cmake.org/files/v{2}/cmake-{1}.tar.gz -O /home/{0}/cmake-{1}.tar.gz'.format(
            os_user, cmake_version, cmake_version.split('.')[0] + "." + cmake_version.split('.')[1]))
        conn.sudo('tar -zxvf cmake-{}.tar.gz'.format(cmake_version))
        with conn.cd('/home/{}/cmake-{}/'.format(os_user, cmake_version)):
            conn.sudo('./bootstrap --prefix=/usr/local && make && make install')
        conn.sudo('ln -s /usr/local/bin/cmake /bin/cmake{}'.format(cmake_version))
        conn.sudo('git clone https://github.com/pytorch/pytorch.git')
        with conn.cd('/home/{}/pytorch/'.format(os_user)):
            conn.sudo('git submodule update --init')
            with settings(warn_only=True):
                conn.sudo('git checkout v{}'.format(caffe2_version))
                conn.sudo('git submodule update --recursive')
            conn.sudo('mkdir build && cd build && cmake{} .. && make "-j$(nproc)" install'.format(cmake_version))
        conn.sudo('touch /home/' + os_user + '/.ensure_dir/caffe2_ensured')


def install_cntk(os_user, cntk_version):
    if not exists(conn,'/home/{}/.ensure_dir/cntk_ensured'.format(os_user)):
        conn.sudo('echo "exclude=*.i386 *.i686" >> /etc/yum.conf')
        manage_pkg('clean', 'remote', 'all')
        manage_pkg('update-minimal --security -y', 'remote', '')
        manage_pkg('-y install --nogpgcheck', 'remote', 'openmpi openmpi-devel')
        conn.sudo('pip3.5 install https://cntk.ai/PythonWheel/GPU/cntk-{}-cp35-cp35m-linux_x86_64.whl --no-cache-dir'.format(cntk_version))
        conn.sudo('touch /home/{}/.ensure_dir/cntk_ensured'.format(os_user))


def install_keras(os_user, keras_version):
    if not exists(conn,'/home/{}/.ensure_dir/keras_ensured'.format(os_user)):
        conn.sudo('pip3.5 install keras=={} --no-cache-dir'.format(keras_version))
        conn.sudo('touch /home/{}/.ensure_dir/keras_ensured'.format(os_user))


def install_theano(os_user, theano_version):
    if not exists(conn,'/home/{}/.ensure_dir/theano_ensured'.format(os_user)):
        conn.sudo('python3.8 -m pip install Theano=={} --no-cache-dir'.format(theano_version))
        conn.sudo('touch /home/{}/.ensure_dir/theano_ensured'.format(os_user))


def install_mxnet(os_user, mxnet_version):
    if not exists(conn,'/home/{}/.ensure_dir/mxnet_ensured'.format(os_user)):
        conn.sudo('pip3.5 install mxnet-cu80=={} opencv-python --no-cache-dir'.format(mxnet_version))
        conn.sudo('touch /home/{}/.ensure_dir/mxnet_ensured'.format(os_user))


#def install_torch(os_user):
#    if not exists(conn,'/home/{}/.ensure_dir/torch_ensured'.format(os_user)):
#        run('git clone https://github.com/torch/distro.git ~/torch --recursive')
#        with cd('/home/{}/torch/'.format(os_user)):
#            manage_pkg('-y install --nogpgcheck', 'remote', 'cmake curl readline-devel ncurses-devel gcc-c++ gcc-gfortran git gnuplot unzip libjpeg-turbo-devel libpng-devel ImageMagick GraphicsMagick-devel fftw-devel sox-devel sox zeromq3-devel qt-devel qtwebkit-devel sox-plugins-freeworld qt-devel')
#            run('./install.sh -b')
#        run('source /home/{}/.bashrc'.format(os_user))
#        conn.sudo('touch /home/{}/.ensure_dir/torch_ensured'.format(os_user))


def install_gitlab_cert(os_user, certfile):
    try:
        conn.sudo('mv -f /home/{0}/{1} /etc/pki/ca-trust/source/anchors/{1}'.format(os_user, certfile))
        conn.sudo('update-ca-trust')
    except Exception as err:
        print('Failed to install gitlab certificate.{}'.format(str(err)))
