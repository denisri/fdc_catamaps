#!/bin/sh

wget http://threejs.org/build/three.js
# wget https://raw.githubusercontent.com/mrdoob/three.js/master/examples/js/controls/OrbitControls.js
wget https://raw.githubusercontent.com/mrdoob/three.js/master/examples/js/loaders/OBJLoader.js
wget https://raw.githubusercontent.com/mrdoob/three.js/master/examples/js/loaders/MTLLoader.js

# wget https://raw.githubusercontent.com/mrdoob/three.js/master/examples/js/loaders/OBJLoader2.js
# wget https://raw.githubusercontent.com/mrdoob/three.js/master/examples/js/loaders/MTLLoader.js
wget https://raw.githubusercontent.com/mrdoob/three.js/master/examples/js/controls/TrackballControls.js
wget https://code.jquery.com/jquery-3.2.1.min.js
mv jquery-3.2.1.min.js jquery.js
