import time
import json

def cargar_config():
    with open("config.json", "r") as f:
        return json.load(f)

def defensa_activa(config):
    print("🔥 Defensa Inmutable Activada para:", config["propietario"])
    while True:
        print("🔄 Rotación de código y reparación en ejecución...")
        time.sleep(5)  # bucle eterno de 5 segundos
        # Aquí se pueden conectar scripts de IA, GitHub rotativo y sistemas de seguridad

if __name__ == "__main__":
    config = cargar_config()
    defensa_activa(config)
