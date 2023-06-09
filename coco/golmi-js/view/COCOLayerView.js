$(document).ready(function () {

    /**
     * Extends the generic View class by implementations of the drawing
     * functions.
     * This class works with three stacked canvas layers: the 'background'
     * holds a grid and optionally marks target positions for objects, the
     * 'object' layer has all static objects (objects not currently gripped,
     * and finally the 'gripper' layer displays grippers as well as objects
     * held by the grippers.
     * The reasoning behind this separation is that these components need to
     * be redrawn in varying frequency: while the background is static unless
     * the game configuration (board dimensions, etc.) or object target
     * positions change, the objects are meant to be manipulated throughout an
     * interaction and might have to be redrawn several times. The gripper as
     * well as the currently gripped objects however change continuously and
     * have to be redrawn constantly.
     * @param {Socket io connection to the server} modelSocket
     * @param {reference to the canvas DOM element to draw the background to}
        bgCanvas
     * @param {reference to the canvas DOM element to draw the static objects
        to} objCanvas
     * @param {reference to the canvas DOM element to draw grippers and
        gripped objects to} grCanvas
     */
    this.CocoLayerView = class CocoLayerView extends document.View {
        constructor(modelSocket, bgCanvas, objCanvas, grCanvas) {
            super(modelSocket);
            // Three overlapping canvas
            this.bgCanvas	= bgCanvas;
            this.objCanvas	= objCanvas;
            this.grCanvas	= grCanvas;

            // array holding the currently gripped objects
            this.grippedObjs = new Array();

            // Empty the canvas
            this.clear();
        }

        // Canvas width in pixels. Assumes all 3 canvas are the same size
        get canvasWidth() {
            return this.bgCanvas.width;
        }

        get canvasHeight() {
            return this.bgCanvas.height;
        }

        // --- drawing functions --- //

        /**
         *  Remove any old drawings.
         */
        clear() {
            // clear all three canvas
            this.clearBg();
            this.clearObj();
            this.clearGr();
        }

        /**
         * Remove old drawings from the background layer.
         */
        clearBg() {
            let ctx = this.bgCanvas.getContext("2d");
            ctx.clearRect(0, 0, this.bgCanvas.width, this.bgCanvas.height);
        }

        /**
         * Remove old drawings from the object layer.
         */
        clearObj() {
            let ctx = this.objCanvas.getContext("2d");
            ctx.clearRect(0, 0, this.objCanvas.width, this.objCanvas.height);
        }

        /**
         * Remove old drawings from the gripper layer.
         */
        clearGr() {
            let ctx = this.grCanvas.getContext("2d");
            ctx.clearRect(0, 0, this.grCanvas.width, this.grCanvas.height);
        }

        /**
         * Draws a grid black on white as the background.
         */
        drawBg() {
            let ctx = this.bgCanvas.getContext("2d");
            // important: https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/clearRect
            // using beginPath() after clear() prevents odd behavior
            ctx.beginPath();
            ctx.fillStyle = "white";
            ctx.lineStyle = "black";
            ctx.lineWidth = 1;

            // white rectangle for background
            ctx.fillRect(0, 0, this.canvasWidth, this.canvasHeight);

            // horizontal lines
            for (let row = 0; row <= this.rows; row++) {
                ctx.moveTo(0, row * this.blockSize);
                ctx.lineTo(this.canvasWidth, row * this.blockSize);
            }
            // vertical lines
            for (let col = 0; col <= this.cols; col++) {
                ctx.moveTo(col * this.blockSize, 0);
                ctx.lineTo(col * this.blockSize, this.canvasHeight);
            }
            // draw to the screen
            ctx.stroke();
        }

        /**
         * Redraw the background.
         * In contrast to drawBg(), this function assumes the background has
         * been drawn before and the old drawing needs to be removed first.
         */
        redrawBg() {
            this.clearBg();
            this.drawBg();
        }

        /**
         * Draw the (static) objects.
         */
        drawObjs() {
            let ctx = this.objCanvas.getContext("2d");
            ctx.beginPath();
            this.plotArrayBoard(ctx, this.objs_grid, this.objs)
        }

        plotArrayBoard(ctx, board, obj_mapping){
            // first plot the objects without borders
            // to avoid artifacts
            for (let [key, value] of Object.entries(board)) {
                let position = key.split(":")
                let i = parseInt(position[0])
                let j = parseInt(position[1])

                for (let obj_idn of value){
                    let this_obj = obj_mapping[obj_idn]
                    this.drawObject(ctx, this_obj, i, j)
                }
            }

            // only plot borders
            for (const object of Object.values(this.objs)){
                if (object.gripped === true){
                    let blockMatrix = object.block_matrix;
    
                    // call drawing helper functions with additional infos
                    let params = {
                        x: object.x,
                        y: object.y,
                    }
                    // draw bounding box around target (there should be only a single one in this experiment)
                    this._drawBB(ctx, blockMatrix, params, "black");
                }
            }
        }

        /**
         * Redraw the (static) objects.
         * In contrast to drawObjs(), this function assumes the objects have
         * been drawn before and the old drawing needs to be removed first.
         */
        redrawObjs() {
            this.clearObj();
            this.drawObjs();
        }

        /**
         * Draw the gripper object and, if applicable, the gripped object.
         * The gripper is used to navigate on the canvas and move objects.
         */
        drawGr() {
            let ctx = this.grCanvas.getContext("2d");
            for (const [grId, gripper] of Object.entries(this.grippers)) {
                // modify style depending on whether an object is gripped
                if (grId === "cell"){

                    // call drawing helper functions with additional infos
                    let params = {
                        x: gripper.x,
                        y: gripper.y,
                    }
                    this._drawBB(ctx, [[1]], params, "red");
                }
            }
        }

        /**
         * Redraw the gripper object and, if applicable, the gripped object.
         * In contrast to drawGr(), this function expects the gripper has been
         * drawn before and the old drawing needs to be removed first.
         */
        redrawGr() {
            this.clearGr();
            this.drawGr();
        }

        drawObject(ctx, obj, i, j){
            switch (obj.type){
                case "screw":
                    this._drawCircle(ctx, obj.x, obj.y, obj.color[1])
                    break;
                case "washer":
                    this._drawDiamond(ctx, obj.x, obj.y, obj.color[1])
                    break;
                case "nut":
                    this._drawBlock(ctx, j, i, obj.color[1]);
                    break;
                case "hbridge":
                    this._drawHBridge(ctx, j, i, obj.color[1]);
                    break;
                case "vbridge":
                    this._drawVBridge(ctx, j, i, obj.color[1]);
                    break;
            }
        }

        // COCOBOT SHAPES
        _drawDiamond(ctx, x, y, color){
            ctx.beginPath();
            x = this._toPxl(x)
            y = this._toPxl(y)

            let width = this.blockSize;
            let height = this.blockSize;

            ctx.moveTo(x + width / 2, y + 2);
            
            // top left edge
            ctx.lineTo(x + 2, y + height / 2);
            
            // bottom left edge
            ctx.lineTo(x + width / 2, y + height - 2);
            
            // bottom right edge
            ctx.lineTo(x + width - 2 , y + height / 2);
            
            // closing the path automatically creates
            // the top right edge
            ctx.closePath();
            
            ctx.fillStyle = color;
            ctx.fill();

            ctx.lineWidth = 2;
            ctx.strokeStyle = 'black';
            ctx.stroke();

            ctx.closePath();
        }

        _drawCircle(ctx, x, y, color){
            ctx.beginPath()
            let circle = new Path2D();
            let padding = this.blockSize / 10;
            let radius = this.blockSize / 2;

            circle.arc(
                this._toPxl(x) + radius,
                this._toPxl(y) + radius,
                radius - padding,
                0, 2 * Math.PI,
                false);

            ctx.fillStyle = color;
            ctx.fill(circle);

            ctx.lineWidth = 2;
            ctx.strokeStyle = 'black';
            ctx.stroke(circle);

            ctx.closePath();
        }

        _drawVBridge(ctx, x, y, color){
            ctx.beginPath();
            ctx.fillStyle = color;
            let padding = this.blockSize / 4;
            let px = this._toPxl(x);
            let py = this._toPxl(y);
            let w = Math.abs(px - this._toPxl(x+1));
            let h =  Math.abs(py - this._toPxl(y+1));
            ctx.fillRect(
                px + padding,
                py,
                w - padding*2,
                h
            );

            ctx.lineWidth = 2;

            // right border
            ctx.beginPath();
            ctx.moveTo(px + padding, py);
            ctx.lineTo(px + padding, py + h);
            ctx.stroke();

            // left border
            ctx.beginPath();
            ctx.moveTo(px + w - padding, py);
            ctx.lineTo(px + w - padding, py + h);
            ctx.stroke();

            ctx.closePath();
        }

        _drawHBridge(ctx, x, y, color){
            ctx.beginPath();
            ctx.fillStyle = color;
            let padding = this.blockSize / 4;
            let px = this._toPxl(x);
            let py = this._toPxl(y);
            let w = Math.abs(px - this._toPxl(x+1));
            let h =  Math.abs(py - this._toPxl(y+1));
            ctx.fillRect(
                px,
                py + padding,
                w,
                h - padding*2
            );

            ctx.lineWidth = 2;

            // upper border
            ctx.beginPath();
            ctx.moveTo(px, py + padding);
            ctx.lineTo(px+w, py + padding);
            ctx.stroke();

            // lower border
            ctx.beginPath();
            ctx.moveTo(px, py + h - padding);
            ctx.lineTo(px+w, py + h - padding);
            ctx.stroke();

            ctx.closePath();
        }

        _drawBB(ctx, bMatrix, params, color) {
            let x = params.x * this.grid_factor
            let y = params.y * this.grid_factor
            // Draw blocks       
            for (let i=0; i< bMatrix[0].length * this.grid_factor; i++) {
                this._drawUpperBorder(ctx, x+i, y, color);
                this._drawLowerBorder(ctx, x+i, (y + bMatrix.length * this.grid_factor -1), color);
            }

            for (let i=0; i< bMatrix.length * this.grid_factor; i++) {
                this._drawLeftBorder(ctx, x, y + i, color);
                this._drawRightBorder(ctx, x + bMatrix[0].length * this.grid_factor -1, y + i, color);
            }
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

        // --- draw helper functions ---
        _drawBlock(ctx, x, y, color) {
            // --- config ---
            ctx.beginPath();
            ctx.fillStyle = color;
            let px = this._toPxl(x);
            let py = this._toPxl(y);
            let w = Math.abs(px - this._toPxl(x+1));
            let h =  Math.abs(py - this._toPxl(y+1));
            ctx.fillRect(px, py, w, h);
            this._drawUpperBorder(ctx, x, y, false)
            this._drawLowerBorder(ctx, x, y, false)
            this._drawLeftBorder(ctx, x, y, false)
            this._drawRightBorder(ctx, x, y, false)
        }

        _drawUpperBorder(
            ctx, x, y, highlight=false, borderColor="black", borderWidth=2) {
            this._drawBorder(ctx, x, y, x+1, y, highlight);
        }

        _drawLowerBorder(
            ctx, x, y, highlight=false, borderColor="black", borderWidth=2) {
            this._drawBorder(ctx, x, y+1, x+1, y+1, highlight);
        }

        _drawLeftBorder(
            ctx, x, y, highlight=false, borderColor="black", borderWidth=2) {
            this._drawBorder(ctx, x, y, x, y+1, highlight);
        }

        _drawRightBorder(
            ctx, x, y, highlight=false, borderColor="black", borderWidth=2) {
            this._drawBorder(ctx, x+1, y, x+1, y+1, highlight);
        }

        _drawBorder(ctx, x1, y1, x2, y2, highlight=false, borderColor="black",
            borderWidth=2) {
            // --- config ---
            // for no highlight, shadowBlur is set to 0 (= invisible)
            // ctx.beginPath();
            ctx.shadowBlur = highlight ? 5 : 0;
            ctx.shadowColor = highlight;
            ctx.lineStyle = borderColor;
            ctx.lineWidth = borderWidth;

            ctx.beginPath();
            ctx.moveTo(this._toPxl(x1), this._toPxl(y1));
            ctx.lineTo(this._toPxl(x2), this._toPxl(y2));
            ctx.stroke();
            ctx.shadowBlur = 0;
            ctx.closePath();
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

    }; // class LayerView end
}); // on document ready end
