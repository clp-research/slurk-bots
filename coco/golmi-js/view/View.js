$(document).ready(function () {
    /**
     * Abstract interface class. Separates the interface into background, objects and grippers
     * which concrete implementations of this view might want to draw separately to improve the
     * performance (the components are static to varying degrees).
     * While drawing functions lack implementations, internal data structures and basic communication
     * with the model are already sketched out in this class.
     * @param {Socket io connection to the server} modelSocket
     */
    this.View = class View {
        constructor(modelSocket) {
            this.socket = modelSocket;
            this._initSocketEvents();

            // Configuration. Is assigned at startDrawing()
            this.cols;			// canvas width in blocks
            this.rows;			// canvas height in blocks
            this.grid_factor;

            // Current state
            this.grippers = new Object();
            this.objs = new Object();
            this.objs_grid = new Object();
            this.targets = new Object();
            this.targets_grid = new Object();
        }

        /**
         * Start listening to events emitted by the model socket. After this
         * initialization, the view reacts to model updates.
         */
        _initSocketEvents() {
            // new state -> redraw object and gripper layer,
            // if targets are given, redraw background
            this.socket.on("update_state", (state) => {
                this.grippers = state["grippers"];
                this.objs = state["objs"];
                this.objs_grid = state["objs_grid"]
                this.targets = state["targets"];
                this.targets_grid = state["targets_grid"]
                this.redraw();
            });
            // new configuration -> save values and redraw everything
            this.socket.on("update_config", (config) => {
                this._loadConfig(config);
                this.redraw();
            });
        }

        // --- getter / setter --- //
        // canvas width in pixels.
        get canvasWidth() {
            console.log("get canvasWidth() at View: not implemented");
            return undefined;
        }

        get canvasHeight() {
            console.log("get canvasHeight() at View: not implemented");
            return undefined;
        }

        get blockSize() {
            return this.canvasWidth/this.cols;
        }

        // --- drawing functions --- //
        /**
         * Draw background, objects, gripper.
         */
        draw() {
            this.drawBg();
            this.drawGr();
            this.drawObjs();
        }

        /**
         * Redraw everything.
         * In contrast to draw(), this function assumes the game has been drawn in the past
         * and the old drawing needs to be removed first.
         */
        redraw() {
            this.clear();
            this.draw();
        }
        /**
         * Loads a configuration received from the model. The values are saved since the configuration is
         * not expected to change frequently.
         * If no configuration is passed, it is requested from the model.
         * Implemented as an async function to make sure the configuration is complete before
         * subsequent steps (i.e. drawing) are made.
         * @param {config object, obtained from the model} config
         */
        _loadConfig(config) {
            // Save all relevant values
            this.cols = config.width * Math.max(1, Math.floor(1/config.move_step));
            this.rows = config.height * Math.max(1, Math.floor(1/config.move_step));
            this.grid_factor = Math.max(1, Math.floor(1/config.move_step))
        }
    }; // class View end
}); // on document ready end
