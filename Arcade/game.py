# Basic arcade shooter 

# Imports
import arcade
import random 


# Constants 
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600 
SCREEN_TITLE = "Arcade Space Shooter"
SCALING = 0.5

class SpaceShooter(arcade.View):
    """Space Shooter side scroller game.
    Player starts on the left, enemies appear on the right.
    Player can move anywhere, but not off screen.
    Enemies fly to the left at variable speed.
    Collisions end the game. 
    You are gay.
    """

    def __init__(self):
        """Initialize the game
        """

        super().__init__()

        #Set up the empty sprite lists
        self.enemies_list = arcade.SpriteList()
        self.clouds_list = arcade.SpriteList()
        self.coin_list = arcade.SpriteList()
        self.all_sprites = arcade.SpriteList()


    def setup(self):
        """Get the game ready to play
        """
        #set the font
        arcade.load_font("fonts/retro.ttf")
        
        # Set the background color
        arcade.set_background_color(arcade.color.SKY_BLUE)


        # Set up the player
        self.player = arcade.Sprite("images/fighter.png", SCALING / 1.7)
        self.player.center_y = self.height / 2
        self.player.left = 10
        self.all_sprites.append(self.player)
        self.paused = False
        #set up the score
        self.score_text = arcade.Text(
            "0",        # stringa iniziale
            self.width / 2,           # centro orizzontale
            self.height - 60,         # poco sotto il bordo superiore
            arcade.color.WHITE,
            50,                       # grandezza carattere
            anchor_x="center",
            font_name="retro"
        )
        self.score = 0

        

        #set the game over flag
        self.game_over = False

        
        # Spawn a new enemy every 0.5 seconds 
        arcade.schedule(self.add_enemy, 0.5)
        # Spawn a new cloud every second 
        arcade.schedule(self.add_cloud, 1.5)
        # Spawn a new coin every second
        arcade.schedule(self.add_coin, 5)



    def add_enemy(self, delta_time: float):
        """Adds a new enemy to the screen
        
        Arguments: 
            delta_time {float} -- How much time has passed since the last call
        """
        if self.paused:
            return
        else:
            # First, create the new enemy sprite
            enemy = FlyingSprite("images/enemy.png", SCALING / 2)

            # Set its position to a random height and off screen right
            enemy.left = random.randint(self.width, self.width + 80)
            enemy.top = random.randint(10, self.height - 10)

            # Set its speed to a random speed heading left
            enemy.velocity = (random.randint(-13, -5), 0)

            # Add it to the enemies list
            self.enemies_list.append(enemy)
            self.all_sprites.append(enemy)

    def add_cloud(self, delta_time: float):
        """Adds a new cloud to the screen 

        Arguments:
            delta_time {float} -- How much time has passed since the last call
        """
        if self.paused:
            return
        else:
            # First, create the new cloud sprite
            cloud = FlyingSprite("images/cloud.png", SCALING/1.2)

            # Set its position to a random height and off screen right
            cloud.left = random.randint(self.width, self.width + 80)
            cloud.top = random.randint(10, self.height - 10)

            # Set its speed to a random speed heading left
            cloud.velocity = (random.randint(-5, -2), 0)

            # Add it to the enemies list
            self.clouds_list.append(cloud)
            self.all_sprites.append(cloud)

            #print(f"Cloud added at position {cloud.left}, {cloud.top}")  # Debug statement

    def add_coin(self, delta_time: float):
        """Adds a new cloud to the screen 

        Arguments:
            delta_time {float} -- How much time has passed since the last call
        """
        if self.paused:
            return
        else:
            # First, create the new cloud sprite
            coin = FlyingSprite("images/coin.png", SCALING/6)
            

            # Set its position to a random height and off screen right, more centered vertically
            coin.left = random.randint(self.width, self.width + 80)
            coin.top = random.randint(50, self.height)

            # Set its speed to a random speed heading left
            coin.velocity = (random.randint(-5, -2), 0)

            # Add it to the enemies list
            self.coin_list.append(coin)
            self.all_sprites.append(coin)

            #print(f"Cloud added at position {cloud.left}, {cloud.top}")  # Debug statement




    def on_draw(self):
        """Draw all game objects
        """
        self.clear()
        self.all_sprites.draw()
        self.score_text.text = f"{self.score}"  #update the score text 
        self.score_text.draw()      #draw the score
    #    arcade.draw_text(
    #        f"{self.score}",
    #        self.width / 2,           # centro orizzontale
    #        self.height - 60,         # poco sotto il bordo superiore
    #        arcade.color.WHITE,
    #        50,                       # grandezza carattere
    #        anchor_x="center",  
    #        font_name="retro"  # deve essere il nome del font, non per forza il file
    #    )
    #    self.score_text.draw()
        #descrive lo stato di sconfitta
        #if self.game_over:
            #arcade.draw_text(
            #    "GAME OVER",
             #   self.width / 2,
              #  self.height / 2,
               # arcade.color.RED,
                #font_size=60,
                #anchor_x="center",
                #font_name="retro"
            #)


    def on_key_press(self, symbol, modifiers):
        """Handle user keyboard input 
        Q: Quit the game
        P: Pause/Unpause the game
        I/J/K/L: Move Up, Left, Down, Right
        Arrows: Move Up, Left, Down, Right

        Arguments: 
            symbol {int} -- Which key was pressed
            modifiers {int} -- Which modifiers were pressed

        """
        if symbol == arcade.key.Q:
            # Quit immediately
            arcade.close_window()

        if symbol == arcade.key.P:
            self.paused = not self.paused

        if symbol == arcade.key.I or symbol == arcade.key.UP:
            self.player.change_y = 5

        if symbol == arcade.key.K or symbol == arcade.key.DOWN:
            self.player.change_y = -5

        if symbol == arcade.key.J or symbol == arcade.key.LEFT:
            self.player.change_x = -5

        if symbol == arcade.key.L or symbol == arcade.key.RIGHT:
            self.player.change_x = 5

    def on_key_release(self, symbol : int, modifiers: int): 
        """Undo movement vectors when movements keys are released

        Arguments: 
            symbol {int} -- Which key was pressed
            modifiers {int} -- Which modifiers were pressed
        """
        if (
            symbol == arcade.key.I
            or symbol == arcade.key.K
            or symbol == arcade.key.UP
            or symbol == arcade.key.DOWN
        ):
            self.player.change_y = 0

        if (
            symbol == arcade.key.J
            or symbol == arcade.key.L
            or symbol == arcade.key.LEFT
            or symbol == arcade.key.RIGHT
        ):
            self.player.change_x = 0


    def on_update(self, delta_time: float):
        """ Update the positions and statuses of all game objects
        If paused, do nothing

        Arguments: 
            delf_time {float} --- Time since the last update
        """

        # If paused, don't update anything
        if self.paused:
            return

        # Did you hit enemies? If so, end the game
        if self.player.collides_with_list(self.enemies_list):
            game_over_view = GameOverView(self.score)
            self.window.show_view(game_over_view)
            # self.game_over = True
            #arcade.close_window()

        if self.player.collides_with_list(self.coin_list):
            if not self.game_over:
                self.score+=1
            for coin in self.player.collides_with_list(self.coin_list):
                coin.remove_from_sprite_lists()
            
               

        # Update everything
        self.all_sprites.update()

        # Keep the player on screen
        if self.player.top > self.height: 
            self.player.top = self.height 
        if self.player.right > self.width:
            self.player.right = self.width
        if self.player.bottom < 0:
            self.player.bottom = 0   
        if self.player.left < 0:
            self.player.left = 0




class FlyingSprite(arcade.Sprite):
    """Base class for all flying sprites.
    Flying sprites include enemies and clouds.
    """

    def update(self,  delta_time: float = 1/60):
        """Update the position of the sprite. 
        When it moves off screen to the left, remove it.
        """

        # Move the sprite
        super().update()

        #print(f"FlyingSprite position: {self.left}, {self.top}")  # Debug statement

        # Remove it off the screen
        if self.right < 0:
            self.remove_from_sprite_lists()

class GameOverView(arcade.View):
    def __init__(self, score):
        super().__init__()
        self.score = score

    #set gameover text
        self.game_over=arcade.Text("GAME OVER",
                         self.window.width / 2,
                         self.window.height / 2 + 40,
                         arcade.color.RED,
                         50,
                         anchor_x="center",
                         font_name="retro")

        self.finalscore=arcade.Text(f"Score: {self.score}",
                         self.window.width / 2,
                         self.window.height / 2,
                         arcade.color.WHITE,
                         30,
                         anchor_x="center",
                         font_name="retro")

        self.restart= arcade.Text("Premi R per ricominciare",
                         self.window.width / 2,
                         self.window.height / 2 - 60,
                         arcade.color.YELLOW,
                         20,
                         anchor_x="center",
                         font_name="retro")

    def on_draw(self):
        self.clear()
        self.game_over.draw()
        self.finalscore.text = f"Score: {self.score}"
        self.finalscore.draw()
        self.restart.draw()

    def on_key_press(self, symbol, modifiers):
        if symbol == arcade.key.R:
            game = SpaceShooter()
            game.setup()
            self.window.show_view(game)
        if symbol == arcade.key.Q:
            # Quit immediately
            arcade.close_window()




# Main code entry point
if __name__ == "__main__":
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    game = SpaceShooter()
    game.setup()
    window.show_view(game)
    arcade.run()

