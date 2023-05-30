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
    this.ReceiverLayerView = class ReceiverLayerView extends document.RecolageLayerView {
        constructor(modelSocket, bgCanvas, objCanvas, grCanvas, show_gripped, show_gripper) {
            super(modelSocket, bgCanvas, objCanvas, grCanvas, show_gripped, show_gripper);
        }
    }; // class LayerView end
}); // on document ready end