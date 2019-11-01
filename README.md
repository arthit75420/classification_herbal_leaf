# classify_herbal_leaf

## My final project

![KU](static/img/logo_ku.jpg)

<p>โครงงานวิศวกรรมคอมพิวเตอร์</p>
<p>ระบบรู้จำและจำแนกใบสมุนไพรพื้นบ้านแบบเรียลไทม์ด้วยการเรียนรู้เชิงลึก</p>
<p>Recognition and classification herbal leaf real time with deep learning</p>
<br>
<p>นายอาทิตย์ นันทะเสนา 5940206026</p>
<p>นายสิทธโชค วงศ์กาฬสินธุ์ 5940205232</p>
<br>
<p>ปริญญานิพนธ์นี้เป็นส่วนหนึ่งของการศึกษาตามหลักสูตรวิศวกรรมศาสตร์บัณฑิต</p>
<p>สาขาวิชาวิศวกรรมศาสตร์คอมพิวเตอร์ คณะวิทยาศาสตร์และวิศวกรรมศาสตร์</p>
<p>มหาวิทยาลัยเกษตรศาสตร์ วิทยาเขตเฉลิมพระเกียรติ จังหวัดสกลนคร</p>
<p>พ.ศ.2562</p>
 

# For use windows

## Resource:

my project use:

* Windows 10 64bit
* Microsoft Powershell for command
* Vscode for codding
* Python 3.7.5
* Tensorflow GPU 1.14 For:
    - Mobilenet V1
    - Inception V3
* Tensorflow GPU 1.15 For:
    - Mobilenet V2

## For install:

Download and install python form: [Python official site](http://www.python.org)

After install python -> install Virtual Enveronment:

Run Powershell

``` powershell
pip install -U pip virtualenv
# `-U` are `--upgrade` 
```

Work in workspace you want and git clone my project.

Eg: _*** you don't forget use powershell for command_

``` powershell
# Here my workspace is `PS C:\Users\MYPC>` 
git clone https://github.com/arthit75420/classification_herbal_leaf.git test_project

# into test_project Folder.
cd test_project
```

Create virtual environment for tf1.14 and tf1.15

``` powershell
# I create vitual environment for tensorflow v.1.14 and use python 3.7.
virtualenv venv_tfgpu1.14_py3.7
```

Activate virtual environment

``` powershell
# run this command for activate you venv.
.\venv_tfgpu1.14_py3.7\Scripts\activate
```

If activate is success display powershell will show like this:

> `(venv_tfgpu1.14_py3.7) PS C:\Users\MYPC\test_project>` 

If activate is error check you virtual environment has created

problem maybe can fixed by run command _ ` *** powershell should run as administrator ***` _

``` powershell
# Here Powershell are Run as Administrator.
PS C:\Windows\system32> Set-ExecutionPolicy Unrestricted -Force

# or maybe this command should run on your workspace.
PS C:\Users\MYPC\test_project> Set-ExecutionPolicy Unrestricted -Force
```

After fixed this problem try activate virtual environment again.

Then after activated:

If use GPU training model install follow hare.

``` powershell
# 1.upgrade pip to latest version.
pip install --upgrade pip

# 2.install Tensorflow GPU
pip install tensorflow-gpu==1.14

# 3.install Flask and APS cheduler
pip install -U Flask
pip install -U Flask-Cors
pip install -U APScheduler
```

If your don't use GPU you can use CPU for training model
 - Just install nomal version : `pip install tensorflow==1.14` 

## Run app:

check you powershell has activate `venv_tfgpu1.14_py3.7` 

you powershell should display 

> _`(venv_tfgpu1.14_py3.7) PS C:\Users\MYPC\test_project>`_

Run this command:

``` powershell
python app.py
```

Open browser link: [localhost:88](http://localhost:88)

Enjoy!!!
## For training model:
check you powershell has activate `venv_tfgpu1.14_py3.7` 

you powershell should display 

> _`(venv_tfgpu1.14_py3.7) PS C:\Users\MYPC\test_project>`_

Run this command for (Re)training:
```powershell
# Current path work directory is c:\Users\MYPC\test_project\
# Change path work directory to `tf` => c:\Users\MYPC\test_project\tf
cd tf

# Run this command
python -m tf_scripts.retrain `
 --bottleneck_dir=tf_files/bottlenecks `
 --how_many_training_steps=500 `
 --model_dir=tf_files/models/ `
 --summaries_dir=tf_files/training_summaries/mobilenet_0.50_224 `
 --output_graph=tf_files/retrained_graph.pb `
 --output_labels=tf_files/retrained_labels.txt `
 --architecture=mobilenet_0.50_224 `
 --image_dir=tf_files/dataset `
 --learning_rate=0.01
```

# Classifying an image
check you powershell has activate `venv_tfgpu1.14_py3.7` 

you powershell should display 

> _`(venv_tfgpu1.14_py3.7) PS C:\Users\MYPC\test_project>`_

Run this command for Classification image:
```powershell
python -m tf_scripts.label_image `
 --graph=tf_files/retrained_graph.pb `
 --image=tf_files/test/test.jpg
```

# For use anaconda

follow in future.

