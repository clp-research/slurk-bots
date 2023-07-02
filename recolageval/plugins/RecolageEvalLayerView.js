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
    this.RecolageEvalLayerView = class GiverLayerView extends document.RecolageLayerView {
        constructor(modelSocket, bgCanvas, objCanvas, grCanvas, show_gripped, show_gripper) {
            super(modelSocket, bgCanvas, objCanvas, grCanvas, show_gripped, show_gripper);
        }

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

            // add targets bounding box
            for (const target of Object.values(this.targets))	{
                let blockMatrix = target.block_matrix;

                // call drawing helper functions with additional infos
                let params = {
                    x: target.x,
                    y: target.y,
                    color: "Cornsilk"
                }
                // draw bounding box around target (there should be only a single one in this experiment)
                this._drawBB(ctx, blockMatrix, params, "blue");
            }
        }

        plotArrayBoard(ctx, board, obj_mapping, color=null, highlight=null){
            // first plot the objects without borders
            // to avoid artifacts
            for (let [key, value] of Object.entries(board)) {
                let position = key.split(":")
                let i = parseInt(position[0])
                let j = parseInt(position[1])

                for (let obj_idn of value){
                    let this_obj = obj_mapping[obj_idn]                    

                    // the color must be overwrittenb
                    let this_color = (color !== null) ? color : this_obj.color[1]
                    this._drawBlock(ctx, j, i, this_color, this_obj.gripped);
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

                    if (value in this.targets){
                        highlight = "blue"
                    }

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
    }; // class LayerView end
}); // on document ready end