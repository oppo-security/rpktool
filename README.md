# rpktool    
A toolkit to unpack, debug and repack an rpk file.
## Requirement

>**NOTE** : **The master branch just work in python3.x ,and will not support python2.x

Install the required python modules with `./requirements.txt`:
```
pip install -r requirements.txt
```
Before running the script, you need to install [nodejs(8.0+)](https://nodejs.org/en/) and haptoolkit(only v0.6.15).    
    
Install haptoolkit@0.6.15:     
```
npm install -g hap-toolkit@0.6.15
```

## How to use:    
```
usage: rpktool.py [-h] [-j] [-d] [-p] path

positional arguments:
  path         path of file/dir you want to process

optional arguments:
  -h, --help   show this help message and exit.
  -j, --js     reformat only .js files, it requires the path of .js as a parameter
  -d, --debug  debug the rpk by haptoolkit
  -p, --pack   repack and sign the rpk by haptoolkit
  -f, --feature  scan features in rpk
```
## e.g.
Unpack the rpk `D:\test.rpk`:    
```
python rpktool.py D:\test.rpk
```
The js file of rpk will be reformated when unpacking. Reformated js file named `*_new.js`

Debug the rpk `D:\test.rpk`:    
```
python rpktool.py -d D:\test.rpk
```
Then you need to open `http://localhost:8000` in a browser and sacn the QrCode with hapdebugger on your Android phone. Download and install hapdebugger for Android [here](https://www.qucikapp.cn/docCenter/post/69)
    
    
Repack the rpk dir `D:\test_rpk` and debug it:
```
python rpktool.py -p -d D:\test_rpk
```
NOTICE: Repacking will delete `.\META-INF\CERT`in dir of unpacked rpk, so make a backup if necessary.     
    
You can also reformat js file `D:\jscode\test.js` by using:
```
python rpktool.py -j D:\jscode\
```
    
You can scan rpk(s)'s features by using:
```
python rpktool.py -f D:\test_rpk\
```
or    
```
python rpktool.py -f D:\test_rpk\test.rpk
```

## Version log:
2019/12/3 **V1.0.0**: new 

2019/12/3 **V1.0.1**: Add for scanning features.

2020/5/12 **V1.0.2**: Add for reformating webpack js file.

2020/5/12 **V1.1.0**: Update to python3.x.

