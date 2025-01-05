/**
 * @author qiao / https://github.com/qiao
 * @author mrdoob / http://mrdoob.com
 * @author alteredq / http://alteredqualia.com/
 * @author WestLangley / http://github.com/WestLangley
 * @author erich666 / http://erichaines.com
 */

// This set of controls performs rotating, moving forward/backward, and
// panning.
//
//    Rotate - left mouse / touch: one finger move
//    Move forward/backward at constant altitude - middle mouse,
//        or mousewheel / touch: two finger spread or squish
//    Pan - right mouse, or arrow keys / touch: three finger swipe
//
// modified from https://github.com/mrdoob/three.js/raw/r100/examples/js/controls/OrbitControls.js

import * as THREE from 'three'


function OrbitControls( object, camera, domElement ) {

	this.object = object;
        this.camera = camera;

	this.domElement = ( domElement !== undefined ) ? domElement : document;

	// Set to false to disable this control
	this.enabled = true;

	// "target" sets the location of focus, where the object orbits around
	this.target = new THREE.Vector3();

	// Set to false to disable rotating
	this.enableRotate = true;
	this.rotateSpeed = 1.0;
	this.keyRotateAngleSpeed = 0.1;

	// Set to false to disable panning
	this.enablePan = true;
	this.keyPanSpeed = 7.0;	// pixels moved per arrow key push

	// Set to false to disable use of the keys
	this.enableKeys = true;

	// The four arrow keys
	this.keys = { LEFT: 37, UP: 38, RIGHT: 39, BOTTOM: 40 };

	// Mouse buttons
	this.mouseButtons = { DRIVE: THREE.MOUSE.LEFT, ORIENT: THREE.MOUSE.MIDDLE, PAN: THREE.MOUSE.RIGHT };

	// for reset
	this.target0 = this.target.clone();
	this.position0 = this.camera.position.clone();
	this.zoom0 = this.camera.zoom;

        this.mode_2d = false;
	this.travel_speed_projection = [0., 0., 0.003, 0., 0.03];

	//
	// public methods
	//

	this.saveState = function () {

		scope.target0.copy( scope.target );
		scope.position0.copy( scope.camera.position );
		scope.zoom0 = scope.camera.zoom;

	};

	this.reset = function () {

		scope.target.copy( scope.target0 );
		scope.camera.position.copy( scope.position0 );
		scope.camera.zoom = scope.zoom0;

		scope.camera.updateProjectionMatrix();
		scope.dispatchEvent( changeEvent );

		scope.update();

		state = STATE.NONE;

	};

	// this method is exposed, but perhaps it would be better if we can make it private...
	this.update = function () {

            var offset = new THREE.Vector3();
            var quat = new THREE.Quaternion().setFromUnitVectors(
                camera.up, new THREE.Vector3( 0, 1, 0 ) );
            var quatInverse = quat.clone().invert();

            var lastPosition = new THREE.Vector3();
            var lastQuaternion = new THREE.Quaternion();

            camera.quaternion.multiply( quaternion );
            quaternion.set( 0, 0, 0, 1 );

            scope.camera.position.add( panOffset );
            panOffset.set( 0, 0, 0 );

            if ( zoomChanged ||
                lastPosition.distanceToSquared( scope.camera.position ) > EPS ||
                8 * ( 1 - lastQuaternion.dot( scope.camera.quaternion ) ) > EPS ) {

                scope.dispatchEvent( changeEvent );

                lastPosition.copy( scope.camera.position );
                lastQuaternion.copy( scope.camera.quaternion );
                zoomChanged = false;

                return true;

            }
            return false;

	};

	this.dispose = function () {

		scope.domElement.removeEventListener( 'contextmenu', onContextMenu, false );
		scope.domElement.removeEventListener( 'mousedown', onMouseDown, false );
		scope.domElement.removeEventListener( 'wheel', onMouseWheel, false );

		scope.domElement.removeEventListener( 'touchstart', onTouchStart, false );
		scope.domElement.removeEventListener( 'touchend', onTouchEnd, false );
		scope.domElement.removeEventListener( 'touchmove', onTouchMove, false );

		document.removeEventListener( 'mousemove', onMouseMove, false );
		document.removeEventListener( 'mouseup', onMouseUp, false );

		window.removeEventListener( 'keydown', onKeyDown, false );

		//scope.dispatchEvent( { type: 'dispose' } ); // should this be added here?

	};

	//
	// internals
	//

	var scope = this;

	var changeEvent = { type: 'change' };
	var startEvent = { type: 'start' };
	var endEvent = { type: 'end' };

	var STATE = { NONE: - 1, ROTATE: 0, DRIVE: 1, PAN: 2, TOUCH_ROTATE: 3, TOUCH_DRIVE: 4, TOUCH_PAN: 5, FLY: 6, TOUCH_FLY: 7, MAP: 8 };

	var state = STATE.NONE;
	var speed_factor = 1.;

	var EPS = 0.000001;

	var panOffset = new THREE.Vector3();
	var zoomChanged = false;

	var rotateStart = new THREE.Vector2();
	var rotateEnd = new THREE.Vector2();
	var rotateDelta = new THREE.Vector2();

	var panStart = new THREE.Vector2();
	var panEnd = new THREE.Vector2();
	var panDelta = new THREE.Vector2();
        var panTouch2Start = new THREE.Vector2();
        var panPinchDistance = 0.;

        var panZStart = new THREE.Vector2();
        var panZEnd = new THREE.Vector2();
        var panZDelta = new THREE.Vector2();

        var panMapStart = new THREE.Vector2();
        var panMapEnd = new THREE.Vector2();
        var panMapDelta = new THREE.Vector2();

        var flyStart = new THREE.Vector2();
        var flyEnd = new THREE.Vector2();
        var flyDelta = new THREE.Vector2();

        var quaternion = new THREE.Quaternion( 0., 0, 0, 1. );

	function rotateLeft( angle )
        {
            // rotate around world z
            var axis = new THREE.Vector3( 0, 0, 1. );
            var invquat = scope.camera.quaternion.clone().invert();
            axis.applyQuaternion( invquat );
            axis.normalize();
            var quat = new THREE.Quaternion();
            quat.setFromAxisAngle( axis, -angle );
            quaternion.multiply( quat );
	}

	function rotateUp ( angle )
        {

            // camera x axis
            var axis = new THREE.Vector3( 1, 0, 0 );
//           console.debug('axis:', axis);
            var quat = new THREE.Quaternion();
            quat.setFromAxisAngle( axis, -angle );
            quaternion.multiply( quat );
//           console.debug('rotateUp2 quat:', quat);

	}

	var panLeft = function () {

		var v = new THREE.Vector3();

		return function panLeft( distance, objectMatrix ) {

			v.setFromMatrixColumn( objectMatrix, 0 ); // get X column of objectMatrix
			v.multiplyScalar( - distance );

			panOffset.add( v );

		};

	}();

	var panUp = function () {

		var v = new THREE.Vector3();

		return function panUp( distance, objectMatrix ) {

                        // v.setFromMatrixColumn( objectMatrix, 1 ); // get Y column of objectMatrix

                        v.x = 0.;
                        v.y = 0.;
                        v.z = 1.;

			v.multiplyScalar( distance );

			panOffset.add( v );

		};

	}();

        var panForward = function () {

                var v = new THREE.Vector3();

                return function panForward( distance, objectMatrix ) {

                        v.setFromMatrixColumn( objectMatrix, 2 ); // get Z column of objectMatrix
                        // fix Z coord
                        v.z = 0;
                        v.normalize();
                        if( v.length() == 0. )
                        {
                                // looking down or up (2D mode): move along y
                                v.setFromMatrixColumn( objectMatrix, 1 ); // get Y column of objectMatrix
                                v.z = 0;
                                v.negate();
                                v.normalize();
                        }

                        v.multiplyScalar( distance );

                        panOffset.add( v );

                };

        }();

	var panForwardFly = function () {

		var v = new THREE.Vector3();

		return function panForwardFly( distance, objectMatrix ) {

			v.setFromMatrixColumn( objectMatrix, 2 ); // get Z column of objectMatrix
			v.multiplyScalar( distance );

			panOffset.add( v );

		};

	}();

        var distanceFactor = function ( distance )
        {
            var z = scope.camera.position.z;
	    var pm = scope.travel_speed_projection;
	    // console.log('z:', z, ', dist factor:', ( Math.abs( scope.camera.position.x * pm[0] + scope.camera.position.x * pm[1] + scope.camera.position.z * pm[2] + pm[3] ) + pm[4] ) );
	    return distance * speed_factor *
		    ( Math.abs( scope.camera.position.x * pm[0]
				+ scope.camera.position.x * pm[1]
				+ scope.camera.position.z * pm[2]
				+ pm[3] )
		      + pm[4] );
        }

	// deltaX and deltaY are in pixels; right and down are positive
	var pan = function () {

		var offset = new THREE.Vector3();

		return function pan( deltaX, deltaY ) {

			var element = scope.domElement === document ? scope.domElement.body : scope.domElement;

			if ( scope.camera.isPerspectiveCamera ) {

				// perspective
				var position = scope.camera.position;
				offset.copy( position ).sub( scope.target );
				var targetDistance = offset.length();

                                if( !scope.mode_2d )
                                {
                                        panLeft( distanceFactor( deltaX ),
                                                 scope.camera.matrix );
                                }
                                panUp( distanceFactor( deltaY ),
                                       scope.camera.matrix );

			} else if ( scope.camera.isOrthographicCamera ) {

				// orthographic
				panLeft( deltaX * ( scope.camera.right - scope.camera.left ) / scope.camera.zoom / element.clientWidth, scope.camera.matrix );
				panUp( deltaY * ( scope.camera.top - scope.camera.bottom ) / scope.camera.zoom / element.clientHeight, scope.camera.matrix );

			} else {

				// camera neither orthographic nor perspective
				console.warn( 'WARNING: OrbitControls.js encountered an unknown camera type - pan disabled.' );
				scope.enablePan = false;

			}

		};

	}();

	// deltaZ is in pixels;
	var panZ = function () {

		var offset = new THREE.Vector3();

		return function panZ( deltaX, deltaZ ) {

			var element = scope.domElement === document ? scope.domElement.body : scope.domElement;

			if ( scope.camera.isPerspectiveCamera ) {

				// perspective
				var position = scope.camera.position;
				offset.copy( position ).sub( scope.target );
				var targetDistance = offset.length();

				rotateLeft( 2 * Math.PI * deltaX / element.clientWidth * scope.rotateSpeed );
				panForward( distanceFactor( deltaZ ), scope.camera.matrix );

			} else if ( scope.camera.isOrthographicCamera ) {

				// orthographic
				rotateLeft( 2 * Math.PI * deltaX / element.clientWidth * scope.rotateSpeed );
				panForward( deltaZ * ( scope.camera.top - scope.camera.bottom ) / scope.camera.zoom / element.clientHeight, scope.camera.matrix );

			} else {

				// camera neither orthographic nor perspective
				console.warn( 'WARNING: OrbitControls.js encountered an unknown camera type - panZ disabled.' );
				scope.enablePan = false;

			}

		};

	}();

        var panMap = function () {

                var offset = new THREE.Vector3();

                return function panMap( deltaX, deltaZ ) {


                        var element = scope.domElement === document ? scope.domElement.body : scope.domElement;

                        if ( scope.camera.isPerspectiveCamera ) {

                                // perspective
                                var position = scope.camera.position;
                                offset.copy( position ).sub( scope.target );
                                var targetDistance = offset.length();

                                panLeft( distanceFactor( -deltaX ),
                                         scope.camera.matrix );
                                panForward( distanceFactor( deltaZ ),
                                            scope.camera.matrix );

                        } else if ( scope.camera.isOrthographicCamera ) {

                                // orthographic
                                panLeft( deltaX * ( scope.camera.right - scope.camera.left ) / scope.camera.zoom / element.clientWidth, scope.camera.matrix );
                                panForward( deltaZ * ( scope.camera.top - scope.camera.bottom ) / scope.camera.zoom / element.clientHeight, scope.camera.matrix );

                        } else {

                                // camera neither orthographic nor perspective
                                console.warn( 'WARNING: OrbitControls.js encountered an unknown camera type - panMap disabled.' );
                                scope.enablePan = false;

                        }

                };

        }();

	// deltaZ is in pixels;
	var fly = function () {

		var offset = new THREE.Vector3();

		return function fly( deltaX, deltaZ ) {

			var element = scope.domElement === document ? scope.domElement.body : scope.domElement;

			if ( scope.camera.isPerspectiveCamera ) {

				// perspective
				var position = scope.camera.position;
				offset.copy( position ).sub( scope.target );
				rotateLeft( 2 * Math.PI * deltaX / element.clientWidth * scope.rotateSpeed );
                                panForwardFly( distanceFactor( deltaZ ),
                                               scope.camera.matrix );

			} else if ( scope.camera.isOrthographicCamera ) {

				// orthographic
				rotateLeft( 2 * Math.PI * deltaX / element.clientWidth * scope.rotateSpeed );
				panForwardFly( deltaZ * ( scope.camera.top - scope.camera.bottom ) / scope.camera.zoom / element.clientHeight, scope.camera.matrix );

			} else {

				// camera neither orthographic nor perspective
				console.warn( 'WARNING: OrbitControls.js encountered an unknown camera type - panZ disabled.' );
				scope.enablePan = false;

			}

		};

	}();


	//
	// event callbacks - update the object state
	//

	function handleMouseDownRotate( event ) {

		//console.log( 'handleMouseDownRotate' );

		rotateStart.set( event.clientX, event.clientY );

	}

	function handleMouseDownPan( event ) {

		//console.log( 'handleMouseDownPan' );

		panStart.set( event.clientX, event.clientY );

	}

	function handleMouseDownPanZ( event ) {

		//console.log( 'handleMouseDownPanZ' );

		panZStart.set( event.clientX, event.clientY );

	}

        function handleMouseDownPanMap( event ) {

                //console.log( 'handleMouseDownPanMap' );

                panMapStart.set( event.clientX, event.clientY );

        }

        function handleMouseDownPanMap( event ) {

                //console.log( 'handleMouseDownPanMap' );

                panMapStart.set( event.clientX, event.clientY );

        }

	function handleMouseDownFly( event ) {

		//console.log( 'handleMouseDownFly' );

		flyStart.set( event.clientX, event.clientY );

	}

	function handleMouseMoveRotate( event ) {

		//console.log( 'handleMouseMoveRotate' );

		rotateEnd.set( event.clientX, event.clientY );
		rotateDelta.subVectors( rotateEnd, rotateStart );

		var element = scope.domElement === document ? scope.domElement.body : scope.domElement;

		// rotating across whole screen goes 360 degrees around
		rotateLeft( -2 * Math.PI * rotateDelta.x / element.clientWidth * scope.rotateSpeed );

		// rotating up and down along whole screen attempts to go 360, but limited to 180
		rotateUp( -2 * Math.PI * rotateDelta.y / element.clientHeight * scope.rotateSpeed );
		rotateStart.copy( rotateEnd );

		scope.update();

	}

	function handleMouseMovePan( event ) {

		// console.log( 'handleMouseMovePan' );

		panEnd.set( event.clientX, event.clientY );

		panDelta.subVectors( panEnd, panStart );

		pan( panDelta.x, panDelta.y );

		panStart.copy( panEnd );

		scope.update();

	}

	function handleMouseMovePanZ( event ) {

		// console.log( 'handleMouseMovePanZ' );

		panZEnd.set( event.clientX, event.clientY );

		panZDelta.subVectors( panZEnd, panZStart );

		panZ( -panZDelta.x, -panZDelta.y );

		panZStart.copy( panZEnd );

		scope.update();

	}

	function handleMouseMovePanMap( event ) {

                // console.log( 'handleMouseMovePanMap' );

                panMapEnd.set( event.clientX, event.clientY );

                panMapDelta.subVectors( panMapEnd, panMapStart );

                panMap( -panMapDelta.x, -panMapDelta.y );

                panMapStart.copy( panMapEnd );

                scope.update();

	}

	function handleMouseMoveFly( event ) {

		// console.log( 'handleMouseMoveFly' );

		flyEnd.set( event.clientX, event.clientY );

		flyDelta.subVectors( flyEnd, flyStart );

		fly( -flyDelta.x, -flyDelta.y );

		flyStart.copy( flyEnd );

		scope.update();

	}

	function handleMouseUp( event ) {

		// console.log( 'handleMouseUp' );

	}

	function handleMouseWheel( event ) {

            // console.log( 'handleMouseWheel' );

//             panZStart( 0, 0 );
//             panZEnd.set( 0, event.deltaY );
            panZ( 0, event.deltaY );

            scope.update();

	}

	function handleKeyDown( event ) {

		//console.log( 'handleKeyDown' );

		switch ( event.keyCode ) {

			case scope.keys.UP:
                                if( event.ctrlKey == true )
                                    fly( 0, -scope.keyPanSpeed );
                                else if( event.shiftKey == true )
                                    rotateUp( scope.keyRotateAngleSpeed );
                                else
                                    panZ( 0, -scope.keyPanSpeed );
				scope.update();
				break;

			case scope.keys.BOTTOM:
                                if( event.ctrlKey == true )
                                    fly( 0, scope.keyPanSpeed );
                                else if( event.shiftKey == true )
                                    rotateUp( -scope.keyRotateAngleSpeed );
                                else
                                    panZ( 0, scope.keyPanSpeed );
				scope.update();
				break;

			case scope.keys.LEFT:
                                if( event.ctrlKey == true )
                                    pan( scope.keyPanSpeed, 0 );
                                else
                                    rotateLeft( -scope.keyRotateAngleSpeed );
				scope.update();
				break;

			case scope.keys.RIGHT:
                                if( event.ctrlKey == true )
                                    pan( -scope.keyPanSpeed, 0 );
                                else
                                    rotateLeft( scope.keyRotateAngleSpeed );
				scope.update();
				break;

		}

	}

	function handleTouchStartRotate( event ) {

		//console.log( 'handleTouchStartRotate' );

		rotateStart.set( event.touches[ 0 ].pageX, event.touches[ 0 ].pageY );

	}

	function handleTouchStartPan( event ) {

		//console.log( 'handleTouchStartPan' );

		panStart.set( event.touches[ 0 ].pageX,
                              event.touches[ 0 ].pageY );
                panTouch2Start.set( event.touches[ 1 ].pageX,
                                    event.touches[ 1 ].pageY );
                var diff = new THREE.Vector2();
                diff.subVectors( panTouch2Start, panStart );
                panPinchDistance = Math.sqrt( diff.x * diff.x
                                              + diff.y * diff.y );

	}

	function handleTouchStartPanZ( event ) {

		//console.log( 'handleTouchStartPanZ' );

		panZStart.set( event.touches[ 0 ].pageX, event.touches[ 0 ].pageY );

	}

	function handleTouchMoveRotate( event ) {

		//console.log( 'handleTouchMoveRotate' );

		rotateEnd.set( event.touches[ 0 ].pageX, event.touches[ 0 ].pageY );
		rotateDelta.subVectors( rotateEnd, rotateStart );

		var element = scope.domElement === document ? scope.domElement.body : scope.domElement;

		// rotating across whole screen goes 360 degrees around
		rotateLeft( -2 * Math.PI * rotateDelta.x / element.clientWidth * scope.rotateSpeed );

		// rotating up and down along whole screen attempts to go 360, but limited to 180
		rotateUp( -2 * Math.PI * rotateDelta.y / element.clientHeight * scope.rotateSpeed );

		rotateStart.copy( rotateEnd );

		scope.update();

	}

	function handleTouchMovePan( event ) {

		//console.log( 'handleTouchMovePan' );
//                 document.getElementById('debug_win').innerHTML = 'TouchMove ' +  event.touches[0].pageX + ' ' + event.touches[0].pageY + ' ' + event.touches[1].pageX + ' ' + event.touches[1].pageY;

		panEnd.set( event.touches[ 0 ].pageX, event.touches[ 0 ].pageY );

		panDelta.subVectors( panEnd, panStart );

                var t2diff = new THREE.Vector2();
                t2diff.set( event.touches[ 1 ].pageX
                            - event.touches[ 0 ].pageX,
                            event.touches[ 1 ].pageY
                            - event.touches[ 0 ].pageY );
                var dist = Math.sqrt( t2diff.x * t2diff.x
                                      + t2diff.y * t2diff.y );
                if( dist > panPinchDistance * 1.1
                    || dist < panPinchDistance * 0.9 )
                {
                    panPinchDistance = dist; // avoid the threshold
                    state = STATE.TOUCH_FLY;
//                     handleTouchMoveFly( event );
                    return;
                }

		pan( panDelta.x, panDelta.y );

		panStart.copy( panEnd );

		scope.update();

	}

	function handleTouchMoveFly( event )
        {
            state = STATE.TOUCH_FLY;
            var t2diff = new THREE.Vector2();
            t2diff.set( event.touches[ 1 ].pageX
                        - event.touches[ 0 ].pageX,
                        event.touches[ 1 ].pageY
                        - event.touches[ 0 ].pageY );
            var dist = Math.sqrt( t2diff.x * t2diff.x + t2diff.y * t2diff.y );
            var dist_diff = panPinchDistance - dist;
            fly( 0, dist_diff );
            panPinchDistance = dist;
            scope.update();
        }

	function handleTouchMovePanZ( event ) {

		//console.log( 'handleTouchMovePanZ' );

		panZEnd.set( event.touches[ 0 ].pageX, event.touches[ 0 ].pageY );

		panZDelta.subVectors( panZEnd, panZStart );

		panZ( -panZDelta.x, -panZDelta.y );

		panZStart.copy( panZEnd );

		scope.update();

	}

	function handleTouchEnd( event ) {

		//console.log( 'handleTouchEnd' );

	}

	//
	// event handlers - FSM: listen for events and reset state
	//

	function onMouseDown( event ) {

		if ( scope.enabled === false ) return;

                event.preventDefault();

		speed_factor = 1.;
		if( event.altKey == true )
		    speed_factor = 0.1;
		else if( event.shiftKey == true )
		    speed_factor = 5.;

		switch ( event.button ) {

			case scope.mouseButtons.DRIVE:

				if ( scope.enablePan == false ) return;

                                if ( scope.mode_2d == true )
                                {
                                    handleMouseDownPanMap( event );
                                    state = STATE.MAP;
                                }
                                else if ( event.ctrlKey == true )
                                {
                                    handleMouseDownFly( event );
                                    state = STATE.FLY;
                                }
                                else
                                {

                                    handleMouseDownPanZ( event );
                                    state = STATE.DRIVE;
                                }

				break;

			case scope.mouseButtons.ORIENT:

				if ( scope.enableRotate === false ) return;

				handleMouseDownRotate( event );

				state = STATE.ROTATE;

				break;

			case scope.mouseButtons.PAN:

				if ( scope.enablePan === false ) return;

				handleMouseDownPan( event );

				state = STATE.PAN;

				break;

                        case scope.mouseButtons.MAP:

                                if ( scope.enablePan === false ) return;

                                handleMouseDownPanMap( event );

                                state = STATE.PAN;

                                break;

		}

		if ( state !== STATE.NONE ) {

			document.addEventListener( 'mousemove', onMouseMove, false );
			document.addEventListener( 'mouseup', onMouseUp, false );

			scope.dispatchEvent( startEvent );

		}

	}

	function onMouseMove( event ) {

		if ( scope.enabled === false ) return;

		event.preventDefault();

		switch ( state ) {

			case STATE.DRIVE:

				if ( scope.enablePan === false ) return;

				handleMouseMovePanZ( event );

				break;

			case STATE.ROTATE:

				if ( scope.enableRotate === false ) return;

				handleMouseMoveRotate( event );

				break;

			case STATE.PAN:

				if ( scope.enablePan === false ) return;

				handleMouseMovePan( event );

				break;

                        case STATE.FLY:

                                if( scope.enablePan == false ) return;

                                handleMouseMoveFly( event );

                                break;

                        case STATE.MAP:

                                if ( scope.enablePan === false ) return;

                                handleMouseMovePanMap( event );

                                break;

		}

	}

	function onMouseUp( event ) {

		if ( scope.enabled === false ) return;

		handleMouseUp( event );

		document.removeEventListener( 'mousemove', onMouseMove, false );
		document.removeEventListener( 'mouseup', onMouseUp, false );

		scope.dispatchEvent( endEvent );

		state = STATE.NONE;

	}

	function onMouseWheel( event ) {

		if ( scope.enabled === false || scope.enableZoom === false || ( state !== STATE.NONE && state !== STATE.ROTATE ) ) return;

		event.preventDefault();
		event.stopPropagation();

		handleMouseWheel( event );

		scope.dispatchEvent( startEvent ); // not sure why these are here...
		scope.dispatchEvent( endEvent );

	}

	function onKeyDown( event ) {

		if ( scope.enabled === false || scope.enableKeys === false || scope.enablePan === false ) return;

		handleKeyDown( event );

	}

	function onTouchStart( event ) {

		if ( scope.enabled === false ) return;

//                 document.getElementById('debug_win').innerHTML = 'touchStart';

		event.preventDefault();
		event.stopPropagation();

		switch ( event.touches.length ) {

			case 1:	// one-fingered touch: rotate

				if ( scope.enableZoom === false ) return;

				handleTouchStartPanZ( event );

				state = STATE.TOUCH_DRIVE;

				break;

			case 2:	// two-fingered touch: dolly

				if ( scope.enablePan === false ) return;

				handleTouchStartPan( event );

				state = STATE.TOUCH_PAN;

				break;

			case 3: // three-fingered touch: pan
				if ( scope.enableRotate === false ) return;

				handleTouchStartRotate( event );

				state = STATE.TOUCH_ROTATE;

				break;

			default:

				state = STATE.NONE;

		}

		if ( state !== STATE.NONE ) {

			scope.dispatchEvent( startEvent );

		}

	}

	function onTouchMove( event ) {

		if ( scope.enabled === false ) return;

		event.preventDefault();
		event.stopPropagation();

		switch ( event.touches.length ) {

			case 1: // one-fingered touch: rotate

				if ( scope.enableZoom === false ) return;
				if ( state !== STATE.TOUCH_DRIVE ) return; // is this needed?...

				handleTouchMovePanZ( event );

				break;

			case 2: // two-fingered touch: dolly

				if ( scope.enablePan === false ) return;
				if ( state == STATE.TOUCH_PAN )
                                    handleTouchMovePan( event );
                                else if( state == STATE.TOUCH_FLY )
                                    handleTouchMoveFly( event );
                                else
                                    return;

				break;

			case 3: // three-fingered touch: pan

				if ( scope.enableRotate === false ) return;
				if ( state !== STATE.TOUCH_ROTATE ) return; // is this needed?...

				handleTouchMoveRotate( event );

				break;

			default:

				state = STATE.NONE;

		}

	}

	function onTouchEnd( event ) {

		if ( scope.enabled === false ) return;

		handleTouchEnd( event );

		scope.dispatchEvent( endEvent );

		state = STATE.NONE;

	}

	function onContextMenu( event ) {

		if ( scope.enabled === false ) return;

		event.preventDefault();
		return false;

	}

	//

	scope.domElement.addEventListener( 'contextmenu', onContextMenu, false );

	scope.domElement.addEventListener( 'mousedown', onMouseDown, false );
	scope.domElement.addEventListener( 'wheel', onMouseWheel, false );

	scope.domElement.addEventListener( 'touchstart', onTouchStart, false );
	scope.domElement.addEventListener( 'touchend', onTouchEnd, false );
	scope.domElement.addEventListener( 'touchmove', onTouchMove, false );

	window.addEventListener( 'keydown', onKeyDown, false );

	// force an update at start

	this.update();

};

OrbitControls.prototype = Object.create( THREE.EventDispatcher.prototype );
OrbitControls.prototype.constructor = THREE.OrbitControls;

Object.defineProperties( OrbitControls.prototype, {

	center: {

		get: function () {

			console.warn( 'THREE.OrbitControls: .center has been renamed to .target' );
			return this.target;

		}

	},

	// backward compatibility

	noZoom: {

		get: function () {

			console.warn( 'THREE.OrbitControls: .noZoom has been deprecated. Use .enableZoom instead.' );
			return ! this.enableZoom;

		},

		set: function ( value ) {

			console.warn( 'THREE.OrbitControls: .noZoom has been deprecated. Use .enableZoom instead.' );
			this.enableZoom = ! value;

		}

	},

	noRotate: {

		get: function () {

			console.warn( 'THREE.OrbitControls: .noRotate has been deprecated. Use .enableRotate instead.' );
			return ! this.enableRotate;

		},

		set: function ( value ) {

			console.warn( 'THREE.OrbitControls: .noRotate has been deprecated. Use .enableRotate instead.' );
			this.enableRotate = ! value;

		}

	},

	noPan: {

		get: function () {

			console.warn( 'THREE.OrbitControls: .noPan has been deprecated. Use .enablePan instead.' );
			return ! this.enablePan;

		},

		set: function ( value ) {

			console.warn( 'THREE.OrbitControls: .noPan has been deprecated. Use .enablePan instead.' );
			this.enablePan = ! value;

		}

	},

	noKeys: {

		get: function () {

			console.warn( 'THREE.OrbitControls: .noKeys has been deprecated. Use .enableKeys instead.' );
			return ! this.enableKeys;

		},

		set: function ( value ) {

			console.warn( 'THREE.OrbitControls: .noKeys has been deprecated. Use .enableKeys instead.' );
			this.enableKeys = ! value;

		}

	},

	staticMoving: {

		get: function () {

			console.warn( 'THREE.OrbitControls: .staticMoving has been deprecated. Use .enableDamping instead.' );
			return ! this.enableDamping;

		},

		set: function ( value ) {

			console.warn( 'THREE.OrbitControls: .staticMoving has been deprecated. Use .enableDamping instead.' );
			this.enableDamping = ! value;

		}

	},

	dynamicDampingFactor: {

		get: function () {

			console.warn( 'THREE.OrbitControls: .dynamicDampingFactor has been renamed. Use .dampingFactor instead.' );
			return this.dampingFactor;

		},

		set: function ( value ) {

			console.warn( 'THREE.OrbitControls: .dynamicDampingFactor has been renamed. Use .dampingFactor instead.' );
			this.dampingFactor = value;

		}

	}

} );

export { OrbitControls };
