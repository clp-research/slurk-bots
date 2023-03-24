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
                console.log(state)
                this.onUpdateState(state) // hook
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
         * Remove any old drawings.
         */
        clear() {
            console.log("clear() at View: not implemented");
        }

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
         * Draw a background to the game.
         */
        drawBg() {
            console.log("drawBg() at View: not implemented");
        }

        /**
         * Redraw the background.
         * In contrast to drawBg(), this function assumes the background has been drawn in the past
         * and the old drawing needs to be removed first.
         */
        redrawBg() {
            console.log("redrawBg() at View: not implemented");
        }

        /**
         * Draw the (static) objects.
         */
        drawObjs() {
            console.log(`drawObjs() at View: not implemented`);
        }

        /**
         * Redraw the (static) objects.
         * In contrast to drawObjs(), this function assumes the objects have been drawn in the past
         * and the old drawing needs to be removed first.
         */
        redrawObjs() {
            console.log(`redrawObjs() at View: not implemented`);
        }

        /**
         * Draw the gripper object (and, depending on the implementation, the gripped object too)
         * The Gripper is used to navigate on the canvas and move objects.
         */
        drawGr() {
            console.log("drawGr() at View: not implemented");
        }

        /**
         * Redraw the gripper object (and, depending on the implementation, the gripped object too).
         * In contrast to drawGr(), this function assumes the gripper has been drawn in the past
         * and the old drawing needs to be removed first.
         */
        redrawGr() {
            console.log("redrawGr() at View: not implemented");
        }

        onUpdateObjects(objs) {
            console.log(`onUpdateObjects() at View: not implemented`);
        }

        onUpdateTargets(targets) {
            console.log(`onUpdateTargets() at View: not implemented`);
        }

        onUpdateState(state) {
            console.log(`onUpdateState() at View: not implemented`);
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


        drawObjs() {
            let ctx = this.objCanvas.getContext("2d");
            ctx.beginPath();
            this.plotArrayBoard(ctx, this.objs_grid, this.objs)

            // add targets bounding box
            for (const object of Object.values(this.objs)){
                if (object.gripped === true){
                    let blockMatrix = object.block_matrix;
    
                    // call drawing helper functions with additional infos
                    let params = {
                        x: object.x,
                        y: object.y,
                    }
                    // draw bounding box around target (there should be only a single one in this experiment)
                    this._drawBB(ctx, blockMatrix, params, "green");
                }
            }
        }

        drawGr() {
            if (this.show_gripper === true){
                let ctx = this.grCanvas.getContext("2d");
                ctx.beginPath()
                for (const [grId, gripper] of Object.entries(this.grippers)) {
                    // modify style depending on whether an object is gripped
                    let grSize = gripper.gripped ? 0.1 : 0.3;
                    grSize = grSize * this.grid_factor
    
                    // draw the gripper itself
                    // --- config ---
                    ctx.strokeStyle = "#000000";
                    ctx.lineWidth = 2;
                    // draw. The gripper as a simple cross
                    // Note: coordinates are at a tiles upper-left corner!
                    // We draw a gripper from that corner to the bottom-right
                    ctx.beginPath();
                    // top-left to bottom-right
    
                    let x = gripper.x * this.grid_factor
                    let y = gripper.y * this.grid_factor
    
                    ctx.moveTo(this._toPxl(x - grSize), this._toPxl(y - grSize));
                    ctx.lineTo(this._toPxl(x + 1 + grSize), this._toPxl(y + 1 + grSize));
                    // bottom-left to top-right
                    ctx.moveTo(this._toPxl(x - grSize), this._toPxl(y + 1 + grSize));
                    ctx.lineTo(this._toPxl(x + 1 + grSize), this._toPxl(y - grSize));
                    ctx.stroke();
                }
            }
        }

        // --- draw helper functions ---
        _drawBB(ctx, bMatrix, params, color) {
            console.log(params)

            let x = params.x * this.grid_factor
            let y = params.y * this.grid_factor
            // Draw blocks       
            for (let i=0; i< bMatrix.length * this.grid_factor; i++) {
                this._drawUpperBorder(ctx, x+i, y, color);
            }
            for (let i=0; i< bMatrix.length * this.grid_factor; i++) {
                this._drawLowerBorder(ctx, x+i, (y + bMatrix.length * this.grid_factor -1), color);
            }
            for (let i=0; i< bMatrix.length * this.grid_factor; i++) {
                this._drawLeftBorder(ctx, x, y + i, color);
            }
            for (let i=0; i< bMatrix.length * this.grid_factor; i++) {
                this._drawRightBorder(ctx, x + bMatrix[0].length * this.grid_factor -1, y + i, color);
            }
        }

        plotArrayBoard(ctx, board, obj_mapping, overwrite_color=null){
            // first plot the objects without borders
            // to avoid artifacts
            for (let [key, value] of Object.entries(board)) {
                let position = key.split(":")
                let i = parseInt(position[0])
                let j = parseInt(position[1])

                for (let obj_idn of value){
                    let this_obj = obj_mapping[obj_idn]                    
                    let highlight = (this_obj.gripped) ? ("black") : (false)

                    // the color must be overwrittenb
                    let color = (overwrite_color !== null) ? overwrite_color : this_obj.color[1]

                    this._drawBlock(ctx, j, i, color, this_obj.gripped);
                }
            }
            // only plot borders
            for (let [key, value] of Object.entries(board)) {
                let position = key.split(":")
                let i = parseInt(position[0])
                let j = parseInt(position[1])

                for (let obj_idn of value){
                    let this_obj = obj_mapping[obj_idn]                    
                    let highlight = (this_obj.gripped) ? ("green") : (false)

                    if (this._isUpperBorder(board, i, j, obj_idn)) {
                        this._drawUpperBorder(ctx, j, i, highlight);
                    }
                    if (this._isLowerBorder(board, i, j, obj_idn)) {
                        this._drawLowerBorder(ctx, j, i, highlight);
                    }
                    if (this._isLeftBorder(board, i, j, obj_idn)) {
                        this._drawLeftBorder(ctx, j, i, highlight);
                    }
                    if (this._isRightBorder(board, i, j, obj_idn)) {
                        this._drawRightBorder(ctx, j, i, highlight);
                    }
                }
            }
        }

        _drawBlock(ctx, x, y, color, lineColor="grey", lineWidth=1) {
            // --- config ---
            ctx.fillStyle = color;
            let px = this._toPxl(x);
            let py = this._toPxl(y);
            let w = Math.abs(px - this._toPxl(x+1));
            let h =  Math.abs(py - this._toPxl(y+1));
            ctx.fillRect(px, py, w, h);
        }

        _drawUpperBorder(
            ctx, x, y, highlight=false, borderColor="black", borderWidth=2) {
            this._drawBorder(ctx, x, y, x+1, y, highlight, borderColor, borderWidth);
        }

        _drawLowerBorder(
            ctx, x, y, highlight=false, borderColor="black", borderWidth=2) {
            this._drawBorder(ctx, x, y+1, x+1, y+1, highlight, borderColor, borderWidth);
        }

        _drawLeftBorder(
            ctx, x, y, highlight=false, borderColor="black", borderWidth=2) {
            this._drawBorder(ctx, x, y, x, y+1, highlight, borderColor, borderWidth);
        }

        _drawRightBorder(
            ctx, x, y, highlight=false, borderColor="black", borderWidth=2) {
            this._drawBorder(ctx, x+1, y, x+1, y+1, highlight, borderColor, borderWidth);
        }

        _drawBorder(ctx, x1, y1, x2, y2, highlight=false, borderColor="black",
            borderWidth=2) {
            // --- config ---
            // for no highlight, shadowBlur is set to 0 (= invisible)
            ctx.shadowBlur = highlight ? 5 : 0;
            ctx.shadowColor = highlight;
            ctx.lineStyle = borderColor;
            ctx.lineWidth = borderWidth;

            ctx.beginPath();
            ctx.moveTo(this._toPxl(x1), this._toPxl(y1));
            ctx.lineTo(this._toPxl(x2), this._toPxl(y2));
            ctx.stroke();
            ctx.shadowBlur = 0;
        }

        _toPxl(coord) {
            return coord * this.blockSize;
        }

        _isUpperBorder(sparse_matrix, row, column, this_obj_idn) {
            if (row === 0){
                return true;
            }

            return this._borderCheck(
                sparse_matrix,
                `${row}:${column}`,
                `${row-1}:${column}`,
                this_obj_idn
            )
        }

        _isLowerBorder(sparse_matrix, row, column, this_obj_idn) {
            if (row === this.rows - 1){
                return true
            }

            return this._borderCheck(
                sparse_matrix,
                `${row}:${column}`,
                `${row+1}:${column}`,
                this_obj_idn
            )
        }

        _isLeftBorder(sparse_matrix, row, column, this_obj_idn) {
            if (column === 0){
                return true
            }

            return this._borderCheck(
                sparse_matrix,
                `${row}:${column}`,
                `${row}:${column-1}`,
                this_obj_idn
            )
        }

        _isRightBorder(sparse_matrix, row, column, this_obj_idn) {
            if (column === this.cols - 1){
                return true
            }

            return this._borderCheck(
                sparse_matrix,
                `${row}:${column}`,
                `${row}:${column+1}`,
                this_obj_idn
            )
        }

        _borderCheck(sparse_matrix, this_cell_coord, other_cell_coord, this_obj_idn) {
            let other_cell = sparse_matrix[other_cell_coord]
            let this_cell = sparse_matrix[this_cell_coord]

            // cell above is empty
            if (!(other_cell_coord in sparse_matrix)){
                return true
            }

            // other cell contains this object and it's the one on top
            if (other_cell.includes(this_obj_idn) && other_cell[other_cell.length - 1] === this_obj_idn){
                return false
            }

            // this object is not the last one in this cell
            if (this_cell.length > 1 && this_cell[this_cell.length - 1] === this_obj_idn){
                return true
            }

            // cell above does not contain this object
            if (!(other_cell.includes(this_obj_idn))) {
                // this object is the one on top of its cell
                if (this_cell[this_cell.length - 1] === this_obj_idn){
                    return true
                }
            }
            return false
        }
    }; // class View end
}); // on document ready end