var config = {
    type: Phaser.AUTO,
    width: 800,
    height: 600,
    backgroundColor: '#eeeeee',
    parent: 'game-area',
    scene: {
        preload: preload,
        create: create
    }
};

var game = new Phaser.Game(config);

function preload ()
{
    this.load.setBaseURL('https://raw.githubusercontent.com/coli-saar/placement-game/main');
    // this.load.setCORS('anonymous');

    this.load.image('cup', 'images/cup.png');
    this.load.image('knife', 'images/knife.png');
    this.load.image('tomato', 'images/tomato.png');
    this.load.image('stove', 'images/stove.png');
    this.load.image('kitchen-table', 'images/kitchen-table.png');
}

function makeObject(self, width, height, id, scale) {
    var x = rand(width);
    var y = rand(height);
    var ret = self.add.image(x, y, id).setScale(scale);

    ret.on('pointerover', function () {
        ret.setTint(0xdddddd);
    });

    ret.on('pointerout', function () {
        ret.clearTint();
    });

    ret.setInteractive();
    self.input.setDraggable(ret);

    return ret;
}

function rand(maxValue) {
    return Math.floor(maxValue * (Math.random() * 0.8 + 0.1));
}

function create ()
{
    // static objects
    var stove = this.add.image(150, 150, 'stove').setScale(0.1);
    var table = this.add.image(400, 300, 'kitchen-table').setScale(0.1);

    // movable objects
    let { width, height } = this.sys.game.canvas;
    var tomato = makeObject(this, width, height, 'tomato', 0.1);
    var knife = makeObject(this, width, height, 'knife', 0.2);
    var cup = makeObject(this, width, height, 'cup', 0.2);

    this.input.on('drag', function (pointer, gameObject, dragX, dragY) {
        gameObject.x = dragX;
        gameObject.y = dragY;
    });
}