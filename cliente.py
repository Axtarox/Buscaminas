import tkinter as tk
import tkinter.messagebox
import asyncio
import websockets
import json

class ClienteBuscaminas:
    def __init__(self, filas=10, columnas=10, minas=15):
        self.filas = filas
        self.columnas = columnas
        self.minas = minas
        self.id_juego = None
        
        # Estado del juego
        self.estado_celdas = [[0 for _ in range(columnas)] for _ in range(filas)]
        self.marcas = [[False for _ in range(columnas)] for _ in range(filas)]
        
        # Configuración de asyncio
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Configuración de Tkinter
        self.ventana = tk.Tk()
        self.ventana.title("Buscaminas Profesional")
        self.ventana.configure(bg='#f0f0f0')
        
        # Contenedor principal
        self.frame_principal = tk.Frame(self.ventana, bg='#f0f0f0')
        self.frame_principal.pack(padx=20, pady=20)
        
        # Frame de estadísticas
        self.frame_estadisticas = tk.Frame(self.ventana, bg='#f0f0f0')
        self.frame_estadisticas.pack(pady=10)
        
        # Contador de minas restantes
        self.label_minas = tk.Label(
            self.frame_estadisticas, 
            text=f"Minas: {self.minas}", 
            font=('Arial', 12, 'bold'),
            bg='#f0f0f0'
        )
        self.label_minas.pack(side=tk.LEFT, padx=10)
        
        # Botones
        self.botones = [[None for _ in range(columnas)] for _ in range(filas)]
        self.crear_interfaz()
        
        # Websocket
        self.websocket = None
        
        # Total de minas para el juego
        self.total_minas = 0
    
    def crear_interfaz(self):
        for x in range(self.filas):
            for y in range(self.columnas):
                boton = tk.Button(
                    self.frame_principal, 
                    width=2, 
                    height=1,
                    font=('Arial', 10, 'bold'),
                    bg='lightgray',
                    relief=tk.RAISED,
                    command=lambda x=x, y=y: self.revelar_celda(x, y)
                )
                # Añadir clic derecho para marcar
                boton.bind('<Button-3>', lambda e, x=x, y=y: self.marcar_bomba(x, y))
                
                boton.grid(
                    row=x, 
                    column=y, 
                    padx=1, 
                    pady=1
                )
                self.botones[x][y] = boton
        
        # Frame de botones de acción
        frame_botones = tk.Frame(self.ventana, bg='#f0f0f0')
        frame_botones.pack(pady=10)
        
        boton_resolver = tk.Button(
            frame_botones, 
            text="Resolver", 
            command=self.resolver,
            bg='#4CAF50',
            fg='white',
            font=('Arial', 10, 'bold')
        )
        boton_resolver.pack(side=tk.LEFT, padx=10)
        
        boton_reiniciar = tk.Button(
            frame_botones, 
            text="Reiniciar", 
            command=self.reiniciar_juego,
            bg='#2196F3',
            fg='white',
            font=('Arial', 10, 'bold')
        )
        boton_reiniciar.pack(side=tk.LEFT)
        
        # Añadir botón de verificar marcas
        boton_verificar = tk.Button(
            frame_botones, 
            text="Verificar Marcas", 
            command=self.verificar_marcas,
            bg='#FFC107',
            fg='black',
            font=('Arial', 10, 'bold')
        )
        boton_verificar.pack(side=tk.LEFT, padx=10)
    
    def marcar_bomba(self, x, y):
        # Si ya está revelada, no hacer nada
        if self.estado_celdas[x][y] != 0:
            return
        
        # Alternar marca de bomba
        self.marcas[x][y] = not self.marcas[x][y]
        
        if self.marcas[x][y]:
            # Marcar con bandera
            self.botones[x][y].config(
                text='🚩', 
                fg='red', 
                bg='lightyellow'
            )
            # Actualizar contador de minas
            minas_marcadas = sum(sum(fila) for fila in self.marcas)
            self.label_minas.config(text=f"Minas: {self.total_minas - minas_marcadas}")
        else:
            # Desmarcar
            self.botones[x][y].config(
                text='', 
                bg='lightgray'
            )
            # Restaurar contador de minas
            minas_marcadas = sum(sum(fila) for fila in self.marcas)
            self.label_minas.config(text=f"Minas: {self.total_minas - minas_marcadas}")
    
    def reiniciar_juego(self):
        # Restaurar estado inicial
        for x in range(self.filas):
            for y in range(self.columnas):
                self.botones[x][y].config(
                    text='', 
                    state=tk.NORMAL, 
                    bg='lightgray',
                    relief=tk.RAISED
                )
                self.estado_celdas[x][y] = 0
                self.marcas[x][y] = False
        
        # Restaurar contador de minas
        self.label_minas.config(text=f"Minas: {self.minas}")
        
        # Volver a iniciar la conexión
        self.loop.create_task(self.conectar_servidor())
    
    async def conectar_servidor(self):
        self.websocket = await websockets.connect("ws://localhost:8766")
        await self.websocket.send(json.dumps({
            'tipo': 'iniciar_juego',
            'filas': self.filas,
            'columnas': self.columnas,
            'minas': self.minas
        }))
        
        # Iniciar escucha de mensajes
        self.loop.create_task(self.escuchar_servidor())
    
    async def escuchar_servidor(self):
        try:
            while True:
                mensaje = await self.websocket.recv()
                datos = json.loads(mensaje)
                
                if datos['tipo'] == 'tablero_creado':
                    self.id_juego = datos['id_juego']
                    self.total_minas = datos['minas_totales']
                    self.label_minas.config(text=f"Minas: {self.total_minas}")
                
                elif datos['tipo'] == 'celda_revelada':
                    x, y = datos['x'], datos['y']
                    valor = datos['valor']
                    self.ventana.after(0, lambda x=x, y=y, valor=valor: self.actualizar_boton(x, y, valor))
                
                elif datos['tipo'] == 'game_over':
                    self.ventana.after(0, lambda: self.mostrar_game_over(datos['mensaje']))
                
                elif datos['tipo'] == 'minas_resueltas':
                    self.ventana.after(0, lambda minas=datos['minas']: self.mostrar_minas(minas))
                
                elif datos['tipo'] == 'juego_ganado':
                    self.ventana.after(0, lambda: self.mostrar_victoria(datos['mensaje']))
                
                elif datos['tipo'] == 'marcas_incorrectas':
                    self.ventana.after(0, lambda: self.mostrar_marcas_incorrectas(datos['mensaje']))
        
        except websockets.exceptions.ConnectionClosed:
            print("Conexión cerrada")
    
    def mostrar_game_over(self, mensaje):
        tk.messagebox.showerror("Game Over", mensaje)
        # Deshabilitar todos los botones
        for fila in self.botones:
            for boton in fila:
                boton.config(state=tk.DISABLED)
    
    def mostrar_victoria(self, mensaje):
        tk.messagebox.showinfo("¡Victoria!", mensaje)
        # Deshabilitar todos los botones
        for fila in self.botones:
            for boton in fila:
                boton.config(state=tk.DISABLED)
    
    def mostrar_marcas_incorrectas(self, mensaje):
        tk.messagebox.showwarning("Marcas Incorrectas", mensaje)
    
    def actualizar_boton(self, x, y, valor):
        # Marcar como revelada
        self.estado_celdas[x][y] = valor
        
        # Si está marcado con bandera, no revelar
        if self.marcas[x][y]:
            return
        
        # Configurar estilo según valor
        color_texto = {
            0: 'gray',
            1: 'blue',
            2: 'green',
            3: 'red',
            4: 'darkblue',
            5: 'maroon',
            6: 'turquoise',
            7: 'black',
            8: 'gray'
        }
        
        self.botones[x][y].config(
            text=str(valor),
            state=tk.DISABLED,
            relief=tk.SUNKEN,
            fg=color_texto.get(valor, 'black'),
            bg='lightcyan'
        )
    
    def mostrar_minas(self, minas):
        for x, y in minas:
            self.botones[x][y].config(bg='red', text='💣')
    
    def revelar_celda(self, x, y):
        # No revelar si está marcada como bomba
        if self.marcas[x][y]:
            return
        
        self.loop.create_task(self.enviar_revelacion(x, y))
    
    async def enviar_revelacion(self, x, y):
        await self.websocket.send(json.dumps({
            'tipo': 'revelar_celda',
            'id_juego': self.id_juego,
            'x': x,
            'y': y
        }))
    
    def resolver(self):
        self.loop.create_task(self.enviar_resolver())
    
    async def enviar_resolver(self):
        await self.websocket.send(json.dumps({
            'tipo': 'resolver',
            'id_juego': self.id_juego
        }))
    
    def verificar_marcas(self):
        # Obtener las posiciones de las marcas
        marcas_posiciones = [
            [x, y] for x in range(self.filas) 
            for y in range(self.columnas) 
            if self.marcas[x][y]
        ]
        
        self.loop.create_task(self.enviar_verificacion_marcas(marcas_posiciones))
    
    async def enviar_verificacion_marcas(self, marcas):
        await self.websocket.send(json.dumps({
            'tipo': 'verificar_marcas',
            'id_juego': self.id_juego,
            'marcas': marcas
        }))
    
    def iniciar(self):
        # Corrutina para iniciar la conexión
        async def iniciar_conexion():
            await self.conectar_servidor()
        
        # Ejecutar la inicialización de conexión
        self.loop.run_until_complete(iniciar_conexion())
        
        # Integrar el event loop de asyncio con Tkinter
        def actualizar_asyncio():
            self.loop.call_soon(self.loop.stop)
            self.loop.run_forever()
            self.ventana.after(50, actualizar_asyncio)
        
        self.ventana.after(50, actualizar_asyncio)
        
        # Iniciar el bucle de Tkinter
        self.ventana.mainloop()

def main():
    cliente = ClienteBuscaminas()
    cliente.iniciar()

if __name__ == "__main__":
    main()