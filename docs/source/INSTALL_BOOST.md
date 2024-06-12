# 

## Download latest boost from:
```
https://www.boost.org/users/download/
```

## Follow installation instruction from:
https://www.boost.org/doc/libs/1_83_0/more/getting_started/unix-variants.html


## Summary: 

* move the downloaded boost_*.tar.bz2 file to a new folder (e.g "boost-ver"), change directory to there and
```
tar --bzip2 -xf boost_*.tar.bz2
```
* move to the new folder boost_* and assuming you want to build boost for python3.10:

* copy "user-config.jam" from tools/build/example/user-config.jam to your $HOME folder and add the line:
```
using python : 3.10 : /usr/bin/python3.10 : /usr/include/python3.10 : /usr/lib/python3.10 ;
```

* set the installation folder to a local folder "./TMP" and select to install python and mpi from the above new boost_* folder:
```
./bootstrap.sh --prefix=./TMP --with-libraries=python,mpi
```

* install boost locally 
```
./b2 install
```
* this should produce the boost libraries and include header in the local installation folder.

* copy the local "boost" subfolder to the standard include path "/usr/local/include"
```
sudo cp -r ./TMP/include/boost /usr/local/include
```
* copy the contents of the local lib subfolder to the standard lib path "/usr/lib"
```
sudo cp  ./TMP/lib/libboost_python310* /usr/lib/
```

* make sure you have the boost libraries in the standard library path "/usr/lib":

```
libboost_python310.a
libboost_python310.so
libboost_python310.so.1.85.0
```
* and the boost headers in the standard include path "/usr/local/include"
