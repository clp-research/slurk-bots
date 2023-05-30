$(document).ready(function () {

    /**
     * Local controller. Can connect to one or more models. In each model, a gripper is created
     * at connection. If a gripperId is passed, an existing gripper with this id is assigned.
     * Otherwise a new gripper is added with the given id or alternatively the session id.
     * The user's keystrokes are used to control the assigned gripper(s) and any gripped object.
     * @param {optional Array of [socket, gripperId], where gripperId can be null, default:null} modelSockets
     */
    this.LocalKeyController = class LocalKeyController {
        constructor(modelSockets=null) {
            // array of model socket-gripperId pairs that are controlled
            this.models = modelSockets ? modelSockets : new Array();

            // assign functions to key codes: [function for keydown, function for keyup, down?]
            // grip and flip are one-time actions, move and rotate are looped
            this.keyAssignment = {
                13: [this.grip, null, false],					// Enter
                32: [this.grip, null, false],					// Space
                37: [this.moveLeft, this.stopMove, false],		// arrow left
                38: [this.moveUp, this.stopMove, false],		// arrow up
                39: [this.moveRight, this.stopMove, false],		// arrow right
                40: [this.moveDown, this.stopMove, false],		// arrow down
                65: [this.rotateLeft, this.stopRotate, false],	// a
                68: [this.rotateRight, this.stopRotate, false],	// d
                83: [this.flip, null, false],					// s
                87: [this.flip, null, false]					// w
            };

            // Set up key listeners
            this._initKeyListener();
            this.can_move = false;
        }

        // --- (Un)Subscribing models ---

        /**
         * Subscribe a new model. Only one subscription per model is allowed,
         * meaning in one model, only one gripper can be controlled!
         * A gripper is controlled once the model sends an 'attach_gripper'
         * event. See requestGripper for manually adding a gripper.
         * @param {socket of the model server to notify} socket
         */
        attachModel(socket) {
            // make sure not to subscribe a model-gripper pair twice
            for (let [existingSocket, g] of this.models) {
                if (existingSocket.id == socket.id) {
                    return;
                }
            }
            // use the id authoratively assigned by the model
            socket.on("attach_gripper", (assignedId) => {
                this.models.push([socket, assignedId]);
            });
        }

        /**
         * Remove a model from the internal list of models to notify. Remove the associated gripper.
         * @param {socket of the model API to unsubscribe} socket
         */
        detachModel(socket) {
            // remove any occurence of the socket
            for (let i = 0; i < this.models.length; i++) {
                if (this.models[i][0].id == socket.id) {
                    this.models[i][0].emit("remove_gripper", this.models[i][1]);
                    this.models.splice(i, 1);
                }
            }
        }

        // --- Notifying subscribed models ---

        /**
         * Notifies all subscribed models that a "grip" should be attempted.
         * @param {reference to LocalKeyController instance (this)} thisArg
         * @param {set to true to request a looped action on the model side} loop
         */
        grip(thisArg, loop) {
            // send an event to each model
            thisArg.models.forEach(([socket, grId]) => {
                socket.emit("grip", {"id": grId, "loop":loop});
            });
        }

        /**
         * Request stopping ongoing looped gripping.
         */
        stopGrip(thisArg) {
            // send a request to each subscribed model
            thisArg.models.forEach(([socket, grId]) => {
                socket.emit("stop_grip", {"id":grId});
            });
        }

        /**
         * Notify models to move the gripper 1 unit to the left.
         * @param {reference to LocalKeyController instance (this)} thisArg
         * @param {set to true to request a looped action on the model side} loop
         */
        moveLeft(thisArg, loop) { thisArg._moveGr(-1, 0, loop); }

        /**
         * Notify models to move the gripper 1 unit up.
         * @param {reference to LocalKeyController instance (this)} thisArg
         * @param {set to true to request a looped action on the model side} loop
         */
        moveUp(thisArg, loop) { thisArg._moveGr(0, -1, loop); }

        /**
         * Notify models to move the gripper 1 unit to the right.
         * @param {reference to LocalKeyController instance (this)} thisArg
         * @param {set to true to request a looped action on the model side} loop
         */
        moveRight(thisArg, loop) { thisArg._moveGr(1, 0, loop); }

        /**
         * Notify models to move the gripper 1 unit down.
         * @param {reference to LocalKeyController instance (this)} thisArg
         * @param {set to true to request a looped action on the model side} loop
         */
        moveDown(thisArg, loop) { thisArg._moveGr(0, 1, loop); }

        /**
         * Helper function to notify models to move the gripper 1 block in a specified direction.
         * @param {number of blocks to move in x direction} dx
         * @param {number of blocks to move in y direction} dy
         * @param {set to true to request a looped action on the model side} loop
         */
        _moveGr(dx, dy, loop) {
            this.models.forEach(([socket, grId]) => {
                socket.emit("move", {"id": grId, "dx": dx, "dy": dy, "loop": loop});
            });
        }

        /**
         * Request stopping an ongoing looped movement.
         */
        stopMove(thisArg) {
            thisArg.models.forEach(([socket, grId]) => {
                socket.emit("stop_move", {"id": grId});
            });
        }

        // --- Reacting to user events ---

        /**
         * Start fresh, delete any keys remembered as currently pressed.
         */
        resetKeys(){
            for (let key of Object.keys(this.keyAssignment)) {
                // set property pressed to false for each key
                this.keyAssignment[key][2] = false;
            }
        }

        /**
         * Register the key listeners to allow gripper manipulation.
         * Notifies the associated models.
         */
        unbindKeyListener() {
            $(document).unbind("keydown");
            $(document).unbind("keyup");
        }

        _initKeyListener() {
            $(document).keydown( e => {
                if (this.can_move === true){
                    if (this._downAssigned(e.keyCode)) {
                        // only progress if the key is not already in state "down"
                        if (!this._isDown(e.keyCode)) {
                            // Change the state to "down". This is done for all keys, not
                            // just loopable ones, to prevent the keydown event from
                            // firing repeatedly if the key is held.
                            this.keyAssignment[e.keyCode][2] = true;
                            // execute the function assigned to the keydown event
                            let loopable = this._upAssigned(e.keyCode);
                            this.keyAssignment[e.keyCode][0](this, loopable);
                        }
                    }
                }
            });

            $(document).keyup( e => {
                if (this.can_move === true){
                    // check if a function is assigned. Only execute if the key was remembered as "down"
                    if (this._upAssigned(e.keyCode) && this._isDown(e.keyCode)) {
                        // execute the function assigned to the keyup event
                        this.keyAssignment[e.keyCode][1](this);
                    }
                    // change the state to "up"
                    if (this._registered(e.keyCode)) {
                        this.keyAssignment[e.keyCode][2] = false;
                    }
                }
            });
        }

        _registered(keyCode) {
            return this.keyAssignment[keyCode] ? true : false;
        }

        /**
         * Check whether a function is assigned to the keydown event of a given key code.
         * @param {int, code of the key in question} keyCode
         * @return bool, true signifying a function is assigned to keydown
         */
        _downAssigned(keyCode) {
            return this._registered(keyCode) && this.keyAssignment[keyCode][0] ? true : false;
        }

        /**
         * Check whether a function is assigned to the keyup event of a given key code.
         * @param {int, code of the key in question} keyCode
         * @return bool, true signifying a function is assigned to keyup
         */
        _upAssigned(keyCode) {
            return this._registered(keyCode) && this.keyAssignment[keyCode][1] ? true : false;
        }

        /**
         * Check whether a key is currently in "down" state aka currently pressed.
         * @return bool, true if the key is "down"
         */
        _isDown(keyCode) {
            return this._registered(keyCode) && this.keyAssignment[keyCode][2] ? true : false;
        }

    }; // class LocalKeyController end
}); // on document ready end