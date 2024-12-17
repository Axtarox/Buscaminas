import asyncio
import websockets
import json
import random

class ServidorBuscaminas:
    def __init__(self):
        self.tableros = {}
        self.marcas_jugador = {}
    
    def crear_tablero(self, filas, columnas, minas):
        # Genera un tablero con distribución aleatoria de minas
        tablero = [[0 for _ in range(columnas)] for _ in range(filas)]
        minas_colocadas = 0
        minas_posiciones = []
        
        while minas_colocadas < minas:
            x = random.randint(0, filas-1)
            y = random.randint(0, columnas-1)
            if tablero[x][y] != -1:
                tablero[x][y] = -1  # Marca mina
                minas_posiciones.append((x, y))
                minas_colocadas += 1
        
        # Calcula números de minas adyacentes
        for x in range(filas):
            for y in range(columnas):
                if tablero[x][y] != -1:
                    tablero[x][y] = self.contar_minas_adyacentes(tablero, x, y)
        
        return tablero, minas_posiciones
    
    def contar_minas_adyacentes(self, tablero, x, y):
        # Cuenta minas alrededor de una celda
        direcciones = [
            (-1,-1), (-1,0), (-1,1),
            (0,-1), (0,1),
            (1,-1), (1,0), (1,1)
        ]
        minas = 0
        filas = len(tablero)
        columnas = len(tablero[0])
        
        for dx, dy in direcciones:
            nx, ny = x + dx, y + dy
            if 0 <= nx < filas and 0 <= ny < columnas and tablero[nx][ny] == -1:
                minas += 1
        
        return minas
    
    async def gestionar_cliente(self, websocket):
        try:
            async for mensaje in websocket:
                datos = json.loads(mensaje)
                
                if datos['tipo'] == 'iniciar_juego':
                    filas = datos['filas']
                    columnas = datos['columnas']
                    minas = datos['minas']
                    
                    # Crear tablero
                    tablero, minas_posiciones = self.crear_tablero(filas, columnas, minas)
                    id_juego = hash(str(tablero))
                    self.tableros[id_juego] = tablero
                    
                    await websocket.send(json.dumps({
                        'tipo': 'tablero_creado',
                        'id_juego': id_juego,
                        'filas': filas,
                        'columnas': columnas,
                        'minas_totales': minas
                    }))
                
                elif datos['tipo'] == 'revelar_celda':
                    id_juego = datos['id_juego']
                    x, y = datos['x'], datos['y']
                    tablero = self.tableros[id_juego]
                    
                    if tablero[x][y] == -1:
                        await websocket.send(json.dumps({
                            'tipo': 'game_over',
                            'mensaje': 'Has tocado una mina'
                        }))
                    else:
                        await websocket.send(json.dumps({
                            'tipo': 'celda_revelada',
                            'x': x,
                            'y': y,
                            'valor': tablero[x][y]
                        }))
                
                elif datos['tipo'] == 'verificar_marcas':
                    id_juego = datos['id_juego']
                    marcas = datos['marcas']
                    tablero = self.tableros[id_juego]
                    
                    # Encontrar las posiciones reales de minas
                    minas_reales = [(x,y) for x in range(len(tablero)) 
                                    for y in range(len(tablero[0])) if tablero[x][y] == -1]
                    
                    # Convertir marcas a tuplas para comparación
                    marcas_tuplas = [tuple(marca) for marca in marcas]
                    
                    # Verificar si las marcas coinciden exactamente con las minas
                    if set(marcas_tuplas) == set(minas_reales):
                        await websocket.send(json.dumps({
                            'tipo': 'juego_ganado',
                            'mensaje': '¡Felicidades! Has marcado todas las minas correctamente'
                        }))
                    else:
                        await websocket.send(json.dumps({
                            'tipo': 'marcas_incorrectas',
                            'mensaje': 'Algunas marcas no son correctas'
                        }))
                
                elif datos['tipo'] == 'resolver':
                    id_juego = datos['id_juego']
                    tablero = self.tableros[id_juego]
                    minas = [(x,y) for x in range(len(tablero)) 
                             for y in range(len(tablero[0])) if tablero[x][y] == -1]
                    
                    await websocket.send(json.dumps({
                        'tipo': 'minas_resueltas',
                        'minas': minas
                    }))
        
        except websockets.exceptions.ConnectionClosed:
            print("Conexión cerrada")
    
    async def iniciar_servidor(self):
        server = await websockets.serve(
            self.gestionar_cliente, 
            "localhost", 
            8766
        )
        await server.wait_closed()

if __name__ == "__main__":
    servidor = ServidorBuscaminas()
    asyncio.run(servidor.iniciar_servidor())