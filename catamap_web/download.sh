#!/bin/sh

wget http://threejs.org/build/three.js
# wget https://raw.githubusercontent.com/mrdoob/three.js/master/examples/js/controls/OrbitControls.js
# https://github.com/mrdoob/three.js/raw/r110/examples/js/controls/wget OrbitControls.js
wget https://raw.githubusercontent.com/mrdoob/three.js/master/examples/jsm/loaders/OBJLoader.js
wget https://raw.githubusercontent.com/mrdoob/three.js/master/examples/jsm/loaders/MTLLoader.js
# wget https://github.com/mrdoob/three.js/blob/dev/examples/jsm/loaders/GLTFLoader.js
wget https://raw.githubusercontent.com/mrdoob/three.js/master/examples/jsm/loaders/GLTFLoader.js
wget https://raw.githubusercontent.com/mrdoob/three.js/master/examples/jsm/utils/BufferGeometryUtils.js

# wget https://raw.githubusercontent.com/mrdoob/three.js/master/examples/js/loaders/OBJLoader2.js
# wget https://raw.githubusercontent.com/mrdoob/three.js/master/examples/js/loaders/MTLLoader.js
wget https://raw.githubusercontent.com/mrdoob/three.js/master/examples/jsm/controls/TrackballControls.js
wget https://code.jquery.com/jquery-3.2.1.min.js
mv jquery-3.2.1.min.js jquery.js
