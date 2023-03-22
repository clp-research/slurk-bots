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
    this.ReceiverLayerView = class ReceiverLayerView extends document.View {
        constructor(modelSocket, bgCanvas, objCanvas, grCanvas, show_gripped, show_gripper) {
            super(modelSocket);
            // Three overlapping canvas
            this.bgCanvas	= bgCanvas;
            this.objCanvas	= objCanvas;
            this.grCanvas	= grCanvas;

            // save mode variable
            this.show_gripped = show_gripped
            this.show_gripper = show_gripper

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

            /** no grid for now
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
            ctx.stroke();**/

            // add targets
            for (const target of Object.values(this.targets))	{
                // for use cases where targets can be gripped: don't draw
                // gripped targets on this layer, should be drawn on the
                // gripper layer instead
                if (target.gripped) { continue; }

                let blockMatrix = target.block_matrix;

                // call drawing helper functions with additional infos
                let params = {
                    x: target.x,
                    y: target.y,
                    color: "Cornsilk"
                }
                this._drawBlockObj(ctx, blockMatrix, params);
            }
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
            // draw each object
            for (const obj of Object.values(this.objs))	{
                // skip any gripped object here
                

                let blockMatrix = obj.block_matrix;

                // call drawing helper functions with additional infos
                let params = {
                    x: obj.x,
                    y: obj.y,
                    color: obj.color[1]
                }
                this._drawBlockObj(ctx, blockMatrix, params);
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
            ctx.beginPath()
            for (const [grId, gripper] of Object.entries(this.grippers)) {
                // draw any gripped object first (i.e. 'below' the gripper)
                if (gripper.gripped) {
                    for (const [grippedId, grippedObj] of Object.entries(gripper.gripped)) {
                        let blockMatrix = grippedObj.block_matrix;

                        if (this.show_gripped === true){
                            let params = {
                                x: grippedObj.x,
                                y: grippedObj.y,
                                color: grippedObj.color[1],
                                highlight: "green" // highlight a gripped object
                            }
                            this._drawBlockObj(ctx,
                                               blockMatrix,
                                               params);
    
                            this._drawBB(ctx, blockMatrix, params, "green");
                        }
                    }
                }

                if (this.show_gripper === true){
                        // modify style depending on whether an object is gripped
                    let grSize = gripper.gripped ? 0.1 : 0.3;

                    // draw the gripper itself
                    // --- config ---
                    ctx.strokeStyle = "#000000";
                    ctx.lineWidth = 2;
                    // draw. The gripper as a simple cross
                    // Note: coordinates are at a tiles upper-left corner!
                    // We draw a gripper from that corner to the bottom-right
                    ctx.beginPath();
                    // top-left to bottom-right
                    ctx.moveTo(this._toPxl(gripper.x - grSize), this._toPxl(gripper.y - grSize));
                    ctx.lineTo(this._toPxl(gripper.x + 1 + grSize), this._toPxl(gripper.y + 1 + grSize));
                    // bottom-left to top-right
                    ctx.moveTo(this._toPxl(gripper.x - grSize), this._toPxl(gripper.y + 1 + grSize));
                    ctx.lineTo(this._toPxl(gripper.x + 1 + grSize), this._toPxl(gripper.y - grSize));
                    ctx.stroke();
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

        _drawBB(ctx, bMatrix, params, color) {
            // Draw blocks       
            for (let i=0; i< bMatrix.length; i++) {
                this._drawUpperBorder(ctx, params.x + i, params.y, color);
            }
            for (let i=0; i< bMatrix.length; i++) {
                this._drawLowerBorder(ctx, params.x + i, params.y + bMatrix.length -1, color);
            }
            for (let i=0; i< bMatrix.length; i++) {
                this._drawLeftBorder(ctx, params.x, params.y + i, color);
            }
            for (let i=0; i< bMatrix.length; i++) {
                this._drawRightBorder(ctx, params.x + bMatrix[0].length -1, params.y + i, color);
            }
        }
        // --- draw helper functions ---

        _drawBlockObj(ctx, bMatrix, params) {
            // Draw blocks
            for (let r=0; r<bMatrix.length;r++) {
                bMatrix[r].forEach((block, c) =>  {
                    if (block) { // draw if matrix field contains a 1
                        let x = params.x + c;
                        let y = params.y + r;
                        this._drawBlock(ctx, x, y, params.color);
                        // draw object borders
                        if (this._isUpperBorder(bMatrix, c, r)) {
                            this._drawUpperBorder(ctx, x, y, params.highlight);
                        }
                        if (this._isLowerBorder(bMatrix, c, r)) {
                            this._drawLowerBorder(ctx, x, y, params.highlight);
                        }
                        if (this._isLeftBorder(bMatrix, c, r)) {
                            this._drawLeftBorder(ctx, x, y, params.highlight);
                        }
                        if (this._isRightBorder(bMatrix, c, r)) {
                            this._drawRightBorder(ctx, x, y, params.highlight);
                        }
                    }
                });
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

        _isUpperBorder(blockMatrix, column, row) {
            // true if 'row' is the top row OR there is no block above
            return row == 0 || blockMatrix[row-1][column] == 0;
        }

        _isLowerBorder(blockMatrix, column, row) {
            // true if 'row' is the bottom row OR there is no block below
            return row == (blockMatrix.length-1) ||
                blockMatrix[row+1][column] == 0;
        }

        _isLeftBorder(blockMatrix, column, row) {
            // true if 'column' is the leftmost column OR there is no block
            // to the left
            return column == 0 || blockMatrix[row][column-1] == 0;
        }

        _isRightBorder(blockMatrix, column, row) {
            // true if 'column' is the rightmost column OR there is no block
            // to the right
            return column == (blockMatrix[row].length-1) ||
                blockMatrix[row][column+1] == 0;
        }

    }; // class LayerView end
}); // on document ready end