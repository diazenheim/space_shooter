# Basic arcade shooter 

# Imports
import arcade
import random 
from pathlib import Path
import os
import json
import tempfile
from datetime import datetime

# Constants 

# --- THEME (NEW) ---
CURRENT_THEME = "day"  # "day" | "night"

STAR_TEXTURE = None
BG_ELEMENT_TEXTURES = {}  # es. {"moon.png": <texture>}


BASE_DIR = Path(__file__).resolve().parent
RECORDS_PATH = BASE_DIR / "records.json"
FONTS_DIR = BASE_DIR / "fonts"

IMAGES_DIR = BASE_DIR / "images"
MUSIC_DIR = BASE_DIR / "music"
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600 
SCREEN_TITLE = "Arcade Space Shooter"
SCALING = 0.5
BGM_STARTED= False
BGM_PLAYER=None

#preload setup
TEXTURES = {}
# subito dopo le costanti
arcade.load_font(str(FONTS_DIR / "retro.ttf"))

def _stop_bgm():
    """Ferma e rilascia il background music player globale."""
    global BGM_STARTED, BGM_PLAYER
    if BGM_PLAYER:
        try:
            BGM_PLAYER.pause()
            BGM_PLAYER.delete()
        except Exception:
            pass
    BGM_PLAYER = None
    BGM_STARTED = False

def apply_theme_background():
    arcade.set_background_color(
        arcade.color.DARK_MIDNIGHT_BLUE if CURRENT_THEME == "night" else arcade.color.SKY_BLUE
    )


#Setting json file and record
def _default_records():
    return {"high_score": 0, "runs": []}

def _load_records():
    """Return dict. If not available use default"""
    try:
        if not RECORDS_PATH.exists():
            return _default_records()
        with open(RECORDS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        # normalizza chiavi mancanti
        return data
    except Exception:
        
        return _default_records()

def _atomic_write_json(path: Path, data: dict):
    """Scrittura atomica: evita file troncati in caso di crash."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="records_", suffix=".json", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)  # atomic on Win/Linux/Mac
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass

def _save_records(data: dict):
    _atomic_write_json(RECORDS_PATH, data)

def get_high_score() -> int:
    return _load_records().get("high_score", 0)

def submit_score(score: int, name: str = "Player") -> dict:
    data = _load_records()
    data["runs"].append({
        "score": int(score),
        "ts": datetime.now().isoformat(timespec="seconds"),
        "name": name
    })
    is_record = False
    if score > data.get("high_score", 0):
        data["high_score"] = int(score)
        is_record = True
    _save_records(data)
    return {"is_record": is_record, "high_score": data["high_score"]}

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
        #Scene with layer
        self.scene : arcade.Scene| None=None

        self.player : arcade.Sprite | None=None
        self.explosion_textures = []
        #UI
        self.score_text : arcade.Text | None=None
        self.heart_text : arcade.Text | None=None

        #state
        self.paused = False
        self.heart = 3
        self.score = 0
        self.killcounter = 0
        self.elapsed_time = 0.0
        self.game_over = False

        #Music
        self.bgm=None
        self.bgm_player=None
        self.music_volume=0.2
        #Sound effects
        self.sfx_exp_1=arcade.load_sound(str(MUSIC_DIR/"explosion_sound_best_1.wav"))
        self.sfx_exp_2=arcade.load_sound(str(MUSIC_DIR/"explosion_sound_best_2.wav"))
        self.sfx_exp_vol=0.4
        self.sfx_exp_vol_2=0.6
        self.sfx_heart=arcade.load_sound(str(MUSIC_DIR/"heart_sound.wav"))
        self.sfx_coin=arcade.load_sound(str(MUSIC_DIR/"coin_sound.wav"))
        
        #Set up the empty sprite lists
        self.enemies_list = arcade.SpriteList()
        self.clouds_list = arcade.SpriteList()
        self.coin_list = arcade.SpriteList()
        self.shoot_list = arcade.SpriteList()
        self.explosion_list = arcade.SpriteList()
        
        self.heart_list = arcade.SpriteList()
        self.star_list = arcade.SpriteList()
        self.all_sprites = arcade.SpriteList()


        #Controller
        self.PAD_SPEED = 5.0    
        self.STICK_DEADZONE = 0.15  
        self.controller = None
        controllers = arcade.get_controllers()

        # If we have any...
        if controllers:
            # Grab the first one in  the list
            self.controller = controllers[0]

            # Open it for input
            self.controller.open()

            # Push this object as a handler for controller events.
            # Required for the controller events to be called.
            self.controller.push_handlers(self)


    def setup(self):
        """Get the game ready to play
        """
        #preloading
        to_preload = [
            "fighter.png",
            "enemy.png",
            "cloud.png",
            "dark_cloud.png",
            "coin.png",
            "shoot_1.png",
            "heart.png",
            "star.png",
            "moon.png"

        ]
        for name in to_preload:
            TEXTURES[name] = arcade.load_texture(str(IMAGES_DIR/name))

    # --- NEW: preload star + moon ---
        global STAR_TEXTURE 
        STAR_TEXTURE = TEXTURES[ "star.png"]
        BG_ELEMENT_TEXTURES["moon.png"]= TEXTURES["moon.png"]
        
        #set explosion textures
        frames_dir = IMAGES_DIR/("explosion")
        frame_paths = sorted(frames_dir.glob("*.png"))  # Assicurati che i nomi siano ordinabili
        self.explosion_textures = [arcade.load_texture(str(p)) for p in frame_paths]    
        
        # Set the background color
        arcade.set_background_color(
            arcade.color.DARK_MIDNIGHT_BLUE if CURRENT_THEME == "night" else arcade.color.SKY_BLUE
        )  

        # --- Scene & layers ---
        self.scene = arcade.Scene()  # <<< CHANGED: creazione Scene
        # Ordine: back → front
        self.scene.add_sprite_list("Background")    # <<< CHANGED    # stelle fisse, gradient, ecc.
        self.scene.add_sprite_list("Stars")         # <<< CHANGED         # stelle dinamiche
        self.scene.add_sprite_list("Clouds")        # <<< CHANGED        # nuvole decorative
        self.scene.add_sprite_list("Actors")        # <<< CHANGED        # player
        self.scene.add_sprite_list("Enemies")       # <<< CHANGED
        self.scene.add_sprite_list("Coins")         # <<< CHANGED
        self.scene.add_sprite_list("Hearts")        # <<< CHANGED
        self.scene.add_sprite_list("Projectiles")   # <<< CHANGED
        self.scene.add_sprite_list("FX")            # <<< CHANGED            # esplosioni

         # Set up the player
        self.player = arcade.Sprite(scale=SCALING / 1.7) 
        self.player.texture = TEXTURES["fighter.png"]       
        self.player.center_y = SCREEN_HEIGHT / 2
        self.player.left = 10
        self.paused = False
        self.scene["Actors"].append(self.player)
        #set up the hearts
        self.heart = 3
        self.heart_text = arcade.Text(
            "0",        # stringa iniziale
            SCREEN_WIDTH -70,           # centro orizzontale
            SCREEN_HEIGHT - 60,         # poco sotto il bordo superiore
            arcade.color.RED,
            50,                       # grandezza carattere
            font_name="retro"
        )
        #set up the score
        self.score_text = arcade.Text(
            "0",        # stringa iniziale
            SCREEN_WIDTH / 2,           # centro orizzontale
            SCREEN_HEIGHT - 60,         # poco sotto il bordo superiore
            arcade.color.WHITE,
            50,                       # grandezza carattere
            anchor_x="center",
            font_name="retro"
        )
        self.score = 0
        self.killcounter = 0
        self.elapsed_time = 0.0
        

       
        global BGM_STARTED, BGM_PLAYER
        if not BGM_STARTED:
            try:
                # scegli il formato che sai funzionare su macOS: OGG/Vorbis o WAV
                music_path = MUSIC_DIR / "retro-music_1.wav"
                self.bgm = arcade.Sound(str(music_path), streaming=True)
                BGM_PLAYER = self.bgm.play(loop=True)
                if BGM_PLAYER:
                    BGM_PLAYER.volume = self.music_volume
                BGM_STARTED = True
                print("[BGM] avviata (prima volta)")
            except Exception as e:
                print("[BGM] errore avvio:", e)
        else:
            # già attiva → aggiorna solo il volume se vuoi
            if BGM_PLAYER:
                BGM_PLAYER.volume = self.music_volume
            print("[BGM] già attiva: non riavvio")

        # importa: tutte le view puntano allo stesso player
        self.bgm_player = BGM_PLAYER
        
        # Spawn a new enemy every 0.5 seconds 
        arcade.schedule(self.add_enemy, 0.5)
        # Spawn a new cloud every second 
        arcade.schedule(self.add_cloud, 1.5)
        # Spawn a new coin every second
        arcade.schedule(self.add_coin, 5)

        # --- NEW: stelle e luna solo in night ---
        if CURRENT_THEME == "night":
            arcade.schedule(self.add_star, 0.35)
            arcade.schedule(self.add_moon, 20.0)
            self.populate_stars(50)

    
    #deallocation
    def on_show_view(self):
    # riallinea il riferimento al player globale (se servisse)
        global BGM_PLAYER
        self.bgm_player = BGM_PLAYER

    def on_hide_view(self):
        self.paused = True


    def add_enemy(self, delta_time: float):
        """Adds a new enemy to the screen
        
        Arguments: 
            delta_time {float} -- How much time has passed since the last call
        """
        if self.paused:
            return
        else:
            # First, create the new enemy sprite
            enemy = FlyingSprite(scale = SCALING / 2)
            enemy.texture = TEXTURES["enemy.png"]


            # Set its position to a random height and off screen right
            enemy.left = random.randint(SCREEN_WIDTH, SCREEN_WIDTH + 80)
            enemy.top = random.randint(10, SCREEN_HEIGHT - 10)

            # Set its speed to a random speed heading left
            enemy.velocity = (random.randint(-13, -5), 0)

            # Add it to the enemies list
            self.scene["Enemies"].append(enemy)
            

    

    def add_cloud(self, delta_time: float):
        """Adds a new cloud to the screen 

        Arguments:
            delta_time {float} -- How much time has passed since the last call
        """
        if self.paused:
            return
        else:
            # First, create the new cloud sprite
            cloud = FlyingSprite(scale=SCALING/1.2)
            # usa la dark cloud se night, altrimenti quella normale
            cloud.texture = TEXTURES["dark_cloud.png"] if CURRENT_THEME == "night" else TEXTURES["cloud.png"]


            # Set its position to a random height and off screen right
            cloud.left = random.randint(SCREEN_WIDTH, SCREEN_WIDTH + 80)
            cloud.top = random.randint(10, SCREEN_HEIGHT - 10)

            # Set its speed to a random speed heading left
            cloud.velocity = (random.randint(-5, -2), 0)

            # Add it to the enemies list
            self.scene["Clouds"].append(cloud)

            #spawn more frequently
            spawn = (self.score+self.elapsed_time**0.7)/10
            i = spawn
            while i > 0.5:
                i -= 0.5
                self.add_enemy(delta_time) 

            #print(f"Cloud added at position {cloud.left}, {cloud.top}")  # Debug statement

    def populate_stars(self, count: int):
        """Popola subito il cielo con un certo numero di stelle quando parte il tema night."""
        if STAR_TEXTURE is None:
            return
        for _ in range(count):
            star = StarSprite(scale=SCALING/23)
            star.texture = STAR_TEXTURE
            star.left = random.randint(0, SCREEN_WIDTH)
            star.center_y = random.randint(0, SCREEN_HEIGHT )
            star.velocity = (-0.5, 0)  # molto lenta
            star.alpha = random.randint(120, 220)        # luminosità variabile
            self.scene["Stars"].append(star)
            

    def add_star(self, delta_time: float):
        if self.paused or STAR_TEXTURE is None or CURRENT_THEME != "night":
            return
        star = StarSprite(scale=SCALING/23)
        star.texture = STAR_TEXTURE
        star.left = random.randint(SCREEN_WIDTH, SCREEN_WIDTH + 80)
        star.center_y = random.randint(0, SCREEN_HEIGHT )
        star.velocity = (-0.5, 0)  # molto lenta
        star.alpha = random.randint(120, 220)        # luminosità variabile
        self.scene["Stars"].append(star)
        print("added star")

    def add_moon(self, delta_time: float):
        if self.paused or "moon.png" not in BG_ELEMENT_TEXTURES or CURRENT_THEME != "night":
            return
        # evita più lune contemporaneamente
        for s in self.scene["Stars"]:
            if getattr(s, "_is_moon", False):
                return
        moon = FlyingSprite(scale=SCALING/7)
        moon.texture = BG_ELEMENT_TEXTURES["moon.png"]
        moon.left = SCREEN_WIDTH + 100
        moon.center_y = int(SCREEN_HEIGHT * random.uniform(0.65, 0.85))
        moon.velocity = (-0.5, 0)
        moon.alpha = 230
        moon._is_moon = True
        self.scene["Stars"].append(moon)

    
    def add_coin(self, delta_time: float):
        """Adds a new cloud to the screen 

        Arguments:
            delta_time {float} -- How much time has passed since the last call
        """
        if self.paused:
            return
        else:
            # First, create the new cloud sprite
            coin = FlyingSprite(scale = SCALING/8)
            coin.texture = TEXTURES["coin.png"]
            

            # Set its position to a random height and off screen right, more centered vertically
            coin.left = random.randint(SCREEN_WIDTH, SCREEN_WIDTH + 80)
            coin.top = random.randint(50, SCREEN_HEIGHT)

            # Set its speed to a random speed heading left
            coin.velocity = (random.randint(-5, -2), 0)

            # Add it to the enemies list
            self.scene["Coins"].append(coin)
           

            #print(f"Cloud added at position {cloud.left}, {cloud.top}")  # Debug statement


    def add_shoot(self):
        if self.paused:
            return
        else:
            # First, create the new cloud sprite
            shoot = FlyingSprite(scale= SCALING/3)
            shoot.texture = TEXTURES["shoot_1.png"]

            # Set its position to a random height and off screen right
            shoot.left = self.player.right
            shoot.top = self.player.center_y

            # Set its speed to a random speed heading left
            shoot.velocity = (7, 0)

            # Add it to the enemies list
            self.scene["Projectiles"].append(shoot)
            

            #print(f"Cloud added at position {cloud.left}, {cloud.top}")  # Debug statement

    def add_heart(self):
            if self.paused:
                return
            else:
                # First, create the new heart sprite
                heart = FlyingSprite(scale = SCALING/9)
                heart.texture = TEXTURES["heart.png"]
                

                # Set its position to a random height and off screen right, more centered vertically
                heart.left = random.randint(SCREEN_WIDTH, SCREEN_WIDTH + 80)
                heart.top = random.randint(50, SCREEN_HEIGHT)

                # Set its speed to a random speed heading left
                heart.velocity = (random.randint(-5, -2), 0)

                # Add it to the heart list
                self.scene["Hearts"].append(heart)
                

                #print(f"Heart added at position {cloud.left}, {cloud.top}")  # Debug statement
    
    
    def on_draw(self):
        """Draw all game objects
        """
        self.clear()
        # --- NEW ---
        self.scene.draw()
        self.score_text.text = f"{self.score}"
        self.heart_text.text=f"{self.heart}"  #update the score text 
        self.heart_text.draw()      #draw the score
        self.score_text.draw()      #draw the score

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
            _stop_bgm()
            arcade.close_window()


        if symbol == arcade.key.P:
            # Pause/unpause the game
            
            pauseview=PauseMenuView(self)
            self.window.show_view(pauseview)
            return

        if symbol == arcade.key.SPACE or symbol == arcade.key.S:
            self.add_shoot()

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


    def on_button_press(self, controller, button_name: str):
        # Spara
        if button_name in ("a", "south", "x"):   # metti quelli che hai
            self.add_shoot()

        # Pausa (menu/start)
        if button_name in ("start", "menu"):
            pauseview = PauseMenuView(self)
            self.window.show_view(pauseview)
            return

        # Quit (opzionale)
        if button_name in ("back", "select"):
            _stop_bgm()
            arcade.close_window()

    def on_button_release(self, controller, button_name: str):
        # Di solito niente qui per un runner 2D
        pass


    def on_stick_motion(self, controller, stick: str, value: float):
        """
        Stick analogici: valori in [-1.0, 1.0]
        Convenzione: 'leftstick' per movimento. (Puoi usare anche 'rightstick' per altro.)
        """
        if self.paused:
            return
        try:
            x, y = float(value.x), float(value.y)
        except AttributeError:
            # value potrebbe essere (x, y)
            try:
                x, y = float(value[0]), float(value[1])
            except Exception:
                x, y = 0.0, 0.0

        if stick == "leftstick":
            # Applica deadzone
            dx = 0.0 if abs(x) < self.STICK_DEADZONE else x
            dy = 0.0 if abs(y) < self.STICK_DEADZONE else y
            self.player.change_x = self.PAD_SPEED * dx
            self.player.change_y = self.PAD_SPEED * dy


    def on_update(self, delta_time: float=1/60):
        """ Update the positions and statuses of all game objects
        If paused, do nothing

        Arguments: 
            delf_time {float} --- Time since the last update
        """

        # If paused, don't update anything
        if self.paused:
            return
        self.elapsed_time += delta_time

        self.scene["Stars"].update()        # <<< CHANGED
        self.scene["Clouds"].update()       # <<< CHANGED
        self.scene["Enemies"].update()      # <<< CHANGED
        self.scene["Coins"].update()        # <<< CHANGED
        self.scene["Hearts"].update()       # <<< CHANGED
        self.scene["Projectiles"].update()  # <<< CHANGED
        self.scene["FX"].update_animation(delta_time)  # <<< CHANGED
        self.scene["Actors"].update()       # <<< CHANGED  # player bounds dopo

        # Did you hit enemies? If so, end the game
        hit_enemies=arcade.check_for_collision_with_list(self.player, self.scene["Enemies"])
        if hit_enemies:
            self.sfx_exp_1.play(volume=self.sfx_exp_vol_2)
            if self.heart != 0:
                self.heart -= 1
                for enemy in hit_enemies:
                    self._spawn_explosion(enemy.center_x, enemy.center_y)
                    enemy.remove_from_sprite_lists()
            else:
                game_over_view = GameOverView(self.score)
                self.window.show_view(game_over_view)
                return
            # self.game_over = True
            #arcade.close_window()
            # Bullets vs enemies
        for bullet in list(self.scene["Projectiles"]):
            hit_list = arcade.check_for_collision_with_list(bullet, self.scene["Enemies"])
            if hit_list:
                bullet.remove_from_sprite_lists()
                self.killcounter +=1
                if self.killcounter % 10 == 0 and self.killcounter != 0:
                    #more complicated
                    if self.heart < 4:
                        self.add_heart()
                    else:
                        if self.score % 2 == 0:
                            self.add_heart()
                        

                for enemy in hit_list:
                    self._spawn_explosion(enemy.center_x, enemy.center_y)
                    self.sfx_exp_2.play(volume=self.sfx_exp_vol)
                    enemy.remove_from_sprite_lists()


        coins_hit=arcade.check_for_collision_with_list(self.player, self.scene["Coins"])
        if coins_hit: 
            if not self.game_over:
                self.sfx_coin.play(volume=self.sfx_exp_vol)
                self.score+=1
            for coin in coins_hit:
                coin.remove_from_sprite_lists()
            
        hearts_hit=arcade.check_for_collision_with_list(self.player, self.scene["Hearts"])
        if hearts_hit:
            if not self.game_over:
                self.sfx_heart.play(volume=self.sfx_exp_vol)
                self.heart+=1
            for heart in hearts_hit:
                heart.remove_from_sprite_lists()
                

        # Keep the player on screen
        if self.player.top > SCREEN_HEIGHT: 
            self.player.top = SCREEN_HEIGHT 
        if self.player.right > SCREEN_WIDTH:
            self.player.right = SCREEN_WIDTH
        if self.player.bottom < 0:
            self.player.bottom = 0   
        if self.player.left < 0:
            self.player.left = 0

    def _spawn_explosion(self, x: float, y: float):
        explosion = Explosion(
            textures=self.explosion_textures,
            frame_time=0.04,
            scale=SCALING * 1.6
        )
        explosion.center_x = x
        explosion.center_y = y
        self.scene["FX"].append(explosion)


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
        if self.right < 0 or self.left > SCREEN_WIDTH+100:
            self.remove_from_sprite_lists()

class GameOverView(arcade.View):
    def __init__(self, score):
        super().__init__()
        self.score = score
        result=submit_score(score)
        self.is_record = result["is_record"]
        self.high_score = result["high_score"]
        self.game_over = None
        self.finalscore = None
        self.resume = None

    #set gameover text
    def on_show_view(self):
        w, h = self.window.width, self.window.height
        self.game_over=arcade.Text("GAME OVER",
                         w / 2,
                         h / 2 + 40,
                         arcade.color.RED,
                         50,
                         anchor_x="center",
                         font_name="retro")

        self.finalscore=arcade.Text(f"Score: {self.score}",
                         w / 2,
                         h / 2,
                         arcade.color.WHITE,
                         30,
                         anchor_x="center",
                         font_name="retro")
        
        self.record_text=arcade.Text(f"New Record: {self.score}",
                         w / 2,
                         h / 2,
                         arcade.color.WHITE,
                         30,
                         anchor_x="center",
                         font_name="retro")

        self.resume= arcade.Text("Premi R per ricominciare",
                         w / 2,
                         h / 2 - 60,
                         arcade.color.YELLOW,
                         20,
                         anchor_x="center",
                         font_name="retro")

    def on_draw(self):
        self.clear()
        self.game_over.draw()
        print(self.is_record)
        if self.is_record:
            self.record_text.text= f"New Record: {self.score}"
            self.record_text.draw()
        else:
            self.finalscore.text = f"Score: {self.score}"
            self.finalscore.draw()
        
        self.resume.draw()

    def on_key_press(self, symbol, modifiers):
        if symbol == arcade.key.R:
            game = SpaceShooter()
            self.window.show_view(game)
            game.setup()
        if symbol == arcade.key.Q:
            # Quit immediately
            _stop_bgm()
            arcade.close_window()


class StarSprite(arcade.Sprite):
    """Stella con leggero 'twinkle'."""
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._twinkle_timer = 0.0

    def update(self, delta_time: float = 1/60):
        super().update()
        if self.right < 0 or self.left > SCREEN_WIDTH + 100:
            self.remove_from_sprite_lists()
        self._twinkle_timer += delta_time
        if self._twinkle_timer >= random.uniform(0.2, 0.5):
            self._twinkle_timer = 0.0
            self.alpha = max(100, min(255, self.alpha + random.randint(-40, 40)))



class Explosion(arcade.Sprite):
    def __init__(self, textures, frame_time=0.04, scale=1.0):
        # textures: lista di arcade.Texture
        super().__init__(scale=scale)
        self.textures = textures
        if not self.textures:
            # fallback: rimuovi subito se mancano i frame
            self.remove_from_sprite_lists()
            return
        self.texture = self.textures[0]
        self._frame_time = frame_time   # secondi per frame (0.04 ≈ 25 fps)
        self._timer = 0.0
        self._index = 0

    def update_animation(self, delta_time: float = 1/60):
        # Avanza i frame in base al tempo
        self._timer += delta_time
        while self._timer >= self._frame_time:
            self._timer -= self._frame_time
            self._index += 1
            if self._index >= len(self.textures):
                self.remove_from_sprite_lists()
                return
            self.texture = self.textures[self._index]


# --- Aggiungi questa classe ---
class PauseMenuView(arcade.View):
    def __init__(self, game_view: "SpaceShooter"):
        super().__init__()
        self.game_view = game_view
        self.game_view.paused = True

        

        w, h = self.window.width, self.window.height
        self.title = arcade.Text("PAUSA", w/2, h/2 + 60, arcade.color.WHITE, 48, anchor_x="center", font_name="retro")
        self.msg1  = arcade.Text("R or P - Resume", w/2, h/2 + 10, arcade.color.YELLOW, 24, anchor_x="center", font_name="retro")
        self.msg2  = arcade.Text("M - Menu", w/2, h/2 - 25, arcade.color.YELLOW, 24, anchor_x="center", font_name="retro")
        self.msg3  = arcade.Text("Q - Quit", w/2, h/2 - 60, arcade.color.YELLOW, 24, anchor_x="center", font_name="retro")

    def draw_rect_lrtb(left, right, top, bottom, color):
        
        if hasattr(arcade, "draw_lrtb_rectangle_filled"):
            arcade.draw_lrtb_rectangle_filled(left, right, top, bottom, color)
        else:
            arcade.draw_lrbt_rectangle_filled(left, right, bottom, top, color)

    
    def on_draw(self):
        # Disegna il gioco “congelato” sotto 
        self.game_view.on_draw()
        PauseMenuView.draw_rect_lrtb(0, self.window.width, self.window.height, 0, (0, 0, 0, 180))
        self.title.draw(); self.msg1.draw(); self.msg2.draw(); self.msg3.draw()

    def on_key_press(self, symbol, modifiers):
        if symbol in (arcade.key.R, arcade.key.P):
            self.game_view.paused = False
            self.window.show_view(self.game_view)
        elif symbol == arcade.key.M:
            self.game_view.paused = True
            main_menu=MainMenuView()
            self.window.show_view(main_menu)
            
            
        elif symbol == arcade.key.Q:
            _stop_bgm()
            arcade.close_window()

class InstructionView(arcade.View):
    def __init__(self, game_view: "SpaceShooter" = None):
        super().__init__()
        self.game_view = game_view
        self.title = self.msg1 = self.msg2 = self.msg3 = self.msg4 = self.msg5 = None
        
    def on_show_view(self):
        w, h = self.window.width, self.window.height
        apply_theme_background()
        self.title = arcade.Text("INSTRUCTIONS", w/2, h/2 + 60, arcade.color.WHITE, 48, anchor_x="center", font_name="retro")
        self.msg1  = arcade.Text("I/J/K/L or Arrows - Move", w/2, h/2 + 10, arcade.color.YELLOW, 24, anchor_x="center", font_name="retro")
        self.msg2  = arcade.Text("SPACE or S - Shoot", w/2, h/2 - 20, arcade.color.YELLOW, 24, anchor_x="center", font_name="retro")
        self.msg3  = arcade.Text("Q - Quit", w/2, h/2 - 50, arcade.color.YELLOW, 24, anchor_x="center", font_name="retro")
        self.msg4  = arcade.Text("M - back to menu", w/2, h/2 - 80, arcade.color.YELLOW, 24, anchor_x="center", font_name="retro")
        self.msg5 = arcade.Text("P - Pause", w/2, h/2 - 115, arcade.color.YELLOW, 24, anchor_x="center", font_name="retro")

    def draw_rect_lrtb(left, right, top, bottom, color):
        if hasattr(arcade, "draw_lrtb_rectangle_filled"):
            arcade.draw_lrtb_rectangle_filled(left, right, top, bottom, color)
        else:
            arcade.draw_lrbt_rectangle_filled(left, right, bottom, top, color)


    def on_draw(self):
        
        if self.game_view is not None:
            self.game_view.on_draw()
            InstructionView.draw_rect_lrtb(0, self.window.width, self.window.height, 0, (0, 0, 0, 140))
        else:
            self.clear()
        self.title.draw(); self.msg1.draw(); self.msg2.draw(); self.msg3.draw(); self.msg4.draw(); self.msg5.draw()

    def on_key_press(self, symbol, modifiers):
        
        if symbol == arcade.key.M:
            main_menu=MainMenuView(self.game_view)
            self.window.show_view(main_menu)
            
        elif symbol == arcade.key.Q:
            _stop_bgm()
            arcade.close_window()

class MainMenuView(arcade.View):
    def __init__(self, game_view: "SpaceShooter" = None):
        super().__init__()
        self.game_view = game_view
        self.title = self.msg1 = self.msg2 = self.msg3 = None
        
    def draw_rect_lrtb(left, right, top, bottom, color):
    
        if hasattr(arcade, "draw_lrtb_rectangle_filled"):
            arcade.draw_lrtb_rectangle_filled(left, right, top, bottom, color)
        else:
            arcade.draw_lrbt_rectangle_filled(left, right, bottom, top, color)


    def on_show_view(self):
        w, h = self.window.width, self.window.height
        apply_theme_background()
        # Titolo (volendo mostra anche il tema corrente)
        self.title = arcade.Text(
            f"MENU  ({CURRENT_THEME.upper()})",
            w / 2, h / 2 + 60,
            arcade.color.WHITE, 48,
            anchor_x="center", font_name="retro"
        )

        # --- Voci aggiornate ---
        self.msg_start = arcade.Text(
            "SPACE - New Game",
            w / 2, h / 2 + 10,
            arcade.color.YELLOW, 24,
            anchor_x="center", font_name="retro"
        )

        self.msg_theme = arcade.Text(
            "D - Day    |    N - Night",
            w / 2, h / 2 - 25,
            arcade.color.YELLOW, 24,
            anchor_x="center", font_name="retro"
        )

        self.msg_settings = arcade.Text(
            "I - Setting",
            w / 2, h / 2 - 60,
            arcade.color.YELLOW, 24,
            anchor_x="center", font_name="retro"
        )

        self.msg_quit = arcade.Text(
            "Q - Quit",
            w / 2, h / 2 - 95,
            arcade.color.YELLOW, 24,
            anchor_x="center", font_name="retro"
        )

    def on_draw(self):
        # Se vuoi mantenere l’effetto “sfondo scurito” quando arrivi dal gioco:
        if self.game_view is not None:
            self.game_view.on_draw()
            MainMenuView.draw_rect_lrtb(0, self.window.width, 0, self.window.height, (0, 0, 0, 140))
        else:
            self.clear()

        # Disegna titolo e voci aggiornate
        # (il titolo mostra anche il tema attuale)
        self.title.text = f"MENU  ({CURRENT_THEME.upper()})"
        self.title.draw()
        self.msg_start.draw()
        self.msg_theme.draw()
        self.msg_settings.draw()
        self.msg_quit.draw()



    def on_key_press(self, symbol, modifiers):
        """Gestione input nel MENU:
        SPACE = New Game | D = Day | N = Night | I = Setting | Q = Quit
        """
        global CURRENT_THEME

        if symbol == arcade.key.SPACE:
            # Avvia un nuovo gioco
            game = SpaceShooter()
            self.window.show_view(game)
            game.setup()

        elif symbol == arcade.key.D:
            # Tema Giorno
            CURRENT_THEME = "day"
            print("[Theme] DAY")
            apply_theme_background()

        elif symbol == arcade.key.N:
            # Tema Notte
            CURRENT_THEME = "night"
            print("[Theme] NIGHT")
            apply_theme_background()

        elif symbol == arcade.key.I:
            # Schermata impostazioni/istruzioni
            instruction_view = InstructionView(self.game_view)
            self.window.show_view(instruction_view)

        elif symbol == arcade.key.Q:
            # Esci dal gioco
            _stop_bgm()
            arcade.close_window()




# Main code entry point
if __name__ == "__main__":
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    main_menu=MainMenuView()
    window.show_view(main_menu)
    arcade.run()
    
