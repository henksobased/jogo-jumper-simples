from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from plyer import accelerometer
from kivy.uix.textinput import TextInput
from kivy.core.audio import SoundLoader
import random
import requests
from kivy.uix.image import Image

FIREBASE_URL = "https://python1-5f124-default-rtdb.firebaseio.com/rank.json"
Window.size = (400, 600)

# Acelerômetro
accelerometer_enabled = False
try:
    accelerometer.enable()
    accelerometer_enabled = True
except:
    print("Acelerômetro não disponível")

class Player(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size = (30, 30)
        self.pos = (185, 100)
        self.img = Image(source='Pixel-Art-Cat-6.webp', size=self.size, pos=self.pos)
        self.add_widget(self.img)
        self.velocity_y = 0

    def update(self):
        self.velocity_y -= 0.5
        x, y = self.pos
        y += self.velocity_y
        self.pos = (x, y)
        self.img.pos = self.pos

    def jump(self):
        self.velocity_y = 10

class Platform(Widget):
    def __init__(self, pos, **kwargs):
        super().__init__(**kwargs)
        self.size = (80, 20)
        self.pos = pos
        self.img = Image(source='platform_pixel.png', size=self.size, pos=self.pos)
        self.add_widget(self.img)

    def update(self):
        self.img.pos = self.pos

class Obstacle(Widget):
    def __init__(self, pos, **kwargs):
        super().__init__(**kwargs)
        self.size = (40, 40)
        self.pos = pos
        self.img = Image(source='spike_pixel.png', size=self.size, pos=self.pos)
        self.add_widget(self.img)

    def update(self):
        self.img.pos = self.pos

def enviar_score_com_nome(nome, score):
    data = {"nome": nome, "score": score}
    try:
        requests.post(FIREBASE_URL, json=data)
    except Exception as e:
        print("Erro ao enviar score:", e)

def buscar_top_scores():
    try:
        response = requests.get(FIREBASE_URL)
        if response.status_code == 200:
            data = response.json()
            if data:
                lista = list(data.values()) if isinstance(data, dict) else data
                lista.sort(key=lambda x: x["score"], reverse=True)
                return lista[:5]
    except Exception as e:
        print("Erro ao buscar ranking:", e)
    return []

class JumperGame(Widget):
    def __init__(self, nome_jogador="Jogador", **kwargs):
        super().__init__(**kwargs)
        self.nome_jogador = nome_jogador
        self.score = 0
        self.morto = False

        # Load sounds
        self.sound_jump = SoundLoader.load('jump.wav')
        self.sound_hit = SoundLoader.load('hit.wav')
        self.sound_gameover = SoundLoader.load('gameover.wav')
        # Force preload
        for s in (self.sound_jump, self.sound_hit, self.sound_gameover):
            if s: s.seek(0)

        self.player = Player()
        self.add_widget(self.player)

        self.platforms = []
        for i in range(6):
            x = random.randint(0, Window.width - 80)
            y = i * 100
            p = Platform((x, y))
            self.platforms.append(p)
            self.add_widget(p)

        self.obstacles = []
        for i in range(4):
            x = random.randint(0, Window.width - 40)
            y = random.randint(200, Window.height)
            obs = Obstacle((x, y))
            self.obstacles.append(obs)
            self.add_widget(obs)

        self.label = Label(text="Score: 0", pos=(10, Window.height - 40))
        self.add_widget(self.label)

        Clock.schedule_interval(self.update, 1/60)

    def update(self, dt):
        if self.morto:
            return

        self.player.update()

        if accelerometer_enabled:
            val = accelerometer.acceleration
            if val:
                tilt_x = val[0]
                px, py = self.player.pos
                px -= tilt_x * 10
                px = max(0, min(Window.width - self.player.width, px))
                self.player.pos = (px, py)
                self.player.img.pos = self.player.pos

        for plat in self.platforms:
            if self.player.collide_widget(plat) and self.player.velocity_y <= 0:
                self.player.jump()
                self.score += 1
                self.label.text = f"Score: {self.score}"
                if self.sound_jump: 
                    self.sound_jump.play()
                break

        for obs in self.obstacles:
            if self.player.collide_widget(obs):
                if self.sound_hit: 
                    self.sound_hit.play()
                self.player.y = -100  # força o Game Over
                break

        if self.player.top > Window.height * 0.6:
            diff = self.player.top - Window.height * 0.6
            self.player.y -= diff
            for plat in self.platforms:
                plat.y -= diff
                plat.pos = (plat.x, plat.y)
                plat.update()
                if plat.top < 0:
                    plat.y = Window.height
                    plat.x = random.randint(0, Window.width - 80)
                    plat.pos = (plat.x, plat.y)
                    plat.update()

            for obs in self.obstacles:
                obs.y -= diff
                obs.pos = (obs.x, obs.y)
                obs.update()
                if obs.top < 0:
                    obs.y = Window.height
                    obs.x = random.randint(0, Window.width - 40)
                    obs.pos = (obs.x, obs.y)
                    obs.update()

        if self.player.y < -50:
            self.morto = True
            self.label.text = "GAME OVER"
            self.label.center_x = Window.width / 2
            self.label.center_y = Window.height / 2
            self.label.font_size = 32
            self.label.color = (1, 0, 0, 1)
            
            if self.sound_gameover: 
                self.sound_gameover.play()

            enviar_score_com_nome(self.nome_jogador, self.score)
            top_scores = buscar_top_scores()
            ranking_text = "\n".join([f"{r['nome']}: {r['score']}" for r in top_scores])

            self.ranking_label = Label(
                text="TOP 5:\n" + ranking_text,
                pos=(10, Window.height / 2 - 120),
                font_size=18,
                halign='left',
                color=(1, 1, 1, 1)
            )
            self.add_widget(self.ranking_label)

class GameScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.game = None

    def start_game(self, nome):
        self.clear_widgets()
        self.game = JumperGame(nome_jogador=nome)
        self.add_widget(self.game)

class RankingScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)

        self.title = Label(text="Ranking Mundial", font_size=32, size_hint=(1, 0.2))
        self.ranking_label = Label(text="Carregando...", font_size=20, halign="left", valign="top")
        self.ranking_label.bind(size=self.ranking_label.setter('text_size'))

        self.btn_voltar = Button(text="Voltar", size_hint=(1, 0.2), font_size=24)
        self.btn_voltar.bind(on_press=self.voltar_menu)

        layout.add_widget(self.title)
        layout.add_widget(self.ranking_label)
        layout.add_widget(self.btn_voltar)
        self.add_widget(layout)

    def on_pre_enter(self):
        top_scores = buscar_top_scores()
        if top_scores:
            texto = "\n".join([f"{i+1}. {r['nome']}: {r['score']}" for i, r in enumerate(top_scores)])
        else:
            texto = "Nenhum score encontrado."
        self.ranking_label.text = texto

    def voltar_menu(self, instance):
        self.manager.current = 'menu'

class MenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', spacing=20, padding=50)

        self.name_input = TextInput(
            hint_text="Digite seu nome",
            multiline=False,
            font_size=24,
            size_hint=(1, 0.2)
        )

        title = Label(text="Jogo de Pulo", font_size=40)
        btn_start = Button(text="Jogar", size_hint=(1, 0.2), font_size=30)
        btn_start.bind(on_press=self.start_game)

        btn_ranking = Button(text="Ver Ranking", size_hint=(1, 0.2), font_size=30)
        btn_ranking.bind(on_press=self.ver_ranking)

        layout.add_widget(title)
        layout.add_widget(self.name_input)
        layout.add_widget(btn_start)
        layout.add_widget(btn_ranking)
        self.add_widget(layout)

    def start_game(self, instance):
        nome = self.name_input.text.strip() or "Jogador"
        self.manager.get_screen('game').start_game(nome)
        self.manager.current = 'game'

    def ver_ranking(self, instance):
        self.manager.current = 'ranking'

class JumperApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(MenuScreen(name='menu'))
        sm.add_widget(GameScreen(name='game'))
        sm.add_widget(RankingScreen(name='ranking'))
        return sm

if __name__ == '__main__':
    JumperApp().run()

