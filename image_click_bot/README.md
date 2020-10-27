## Image Click Bot

This bot is intended to be used to track mouse movements and clicks on an image. Due to certain circumstances,
the only function that has been tested is image loading capability.

### Instructions
1. Open Terminal and start slurk server
2. Open another Terminal and run `image_serve/app.py`. Note that you should put the images under `/image_serve` folder (with .jpg, .png or .tga format). The sequence in which the image is served is random, as it is accessed through a dictionary
3. Create a room using `static/layouts/test_room.json` as layout and an image click task
4. Create a token for image click bot and run `image_click_bot.py`
5. Create user tokens for the task
6. Open browser and log in with the user token(s)
7. You can start the game by typing "start_game" in the dialog box. To skip to the next image, type "skip_image"
