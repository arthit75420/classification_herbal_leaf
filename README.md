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

problem maybe can fixed by run command _` *** powershell should run as administrator ***`_

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
# Run this command
python -m tf.tf_scripts.retrain `
 --how_many_training_steps=500 `
 --architecture=mobilenet_0.50_224 `
 --learning_rate=0.01
```
Parameter you can change it for training you want:
- `--how_many_training_steps` - Default: 4,000
- `--leaning_rate` - Default: 0.01
- `--testing_percentage` precen of image use for test - Default: 10
- `--validation_percentage` precen of image use for test validate - Default: 10
- `--architecture` it are model for use training eg:
    - mobilenet_0.5_244
    - mobilenet_1.0_198
    - The MobileNet is configurable in two ways:
    1. Input image resolution: 128, 160, 192, or 224px. Unsurprisingly, feeding in a higher resolution image takes more processing time, but results in better classification accuracy.
    2. The relative size of the model as a fraction of the largest MobileNet: 1.0, 0.75, 0.50, or 0.25.
- `--summaries_dir` choice you directory to save summaries file for tensorboard

If you want view summaries training use command:
```powershell
# Check path work directory befor run:
tensorboard --logdir tf/tf_files/training_summaries
```
Open browser link: [localhost:6006](http://localhost:6006) to view summaries.

## Train version 2
Run this command for (Re)training:
```powershell
# Run this command
python -m tf.tf_scripts.v2.retrain `
 --how_many_training_steps=500 `
 --summaries_dir=tf/tf_files/training_summaries/inception_v3_500_0.01 `
 --tfhub_module=https://tfhub.dev/google/imagenet/inception_v3/feature_vector/3 `
 --testing_percentage=10 `
 --learning_rate=0.01
```
# Classifying an image
check you powershell has activate `venv_tfgpu1.14_py3.7` 

you powershell should display 

> _`(venv_tfgpu1.14_py3.7) PS C:\Users\MYPC\test_project>`_

Run this command for Classification image:
```powershell
python -m tf.tf_scripts.label_image `
 --graph=tf/tf_files/retrained_graph.pb `
 --image=tf/tf_files/test/test.jpg
```
you will seen results.
# Test accurecy images
```powershell
# inception V3
python -m tf.tf_scripts.tests_image `
 --input_layer=Placeholder `
 --image_dir=tf/tf_files/datatest `
 --input_width=299 `
 --input_height=299
```
Models parameter for use classify images:
* Mobilenet V1
    - `--input_layrt=input`
    - `--input_width=224`
    - `--input_height=224`
* Mobilenet V2
    - `--input_layrt=Mul`
    - `--input_width=299`
    - `--input_height=299`
* Inception V1-4
    - `--input_layrt=Placeholder`
    - `--input_width=299`
    - `--input_height=299`
# For use anaconda

follow in future.

