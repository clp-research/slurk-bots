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
    }; // class LayerView end
}); // on document ready end