from django.core.management.base import BaseCommand
from apps.tanks.models import Lectura, Tanque
from datetime import datetime, timedelta
import random
import numpy as np

class Command(BaseCommand):
    help = "Genera lecturas simuladas con patrones realistas de una estación de servicio"

    def handle(self, *args, **kwargs):
        try:
            # Configuración de los tanques con consumos más realistas
            tanques = [
                {
                    "id": 1, 
                    "capacidad":10000,  # Capacidad más realista
                    "consumo_base": {
                        "hora_pico": (250, 400),     # L/h en horas pico
                        "hora_normal": (150, 250),   # L/h en horas normales
                        "hora_baja": (50, 150)       # L/h en horas bajas
                    },
                    "nombre": "Tanque 93 (Ficticio)"
                },
                {
                    "id": 2, 
                    "capacidad": 25000,
                    "consumo_base": {
                        "hora_pico": (300, 450),
                        "hora_normal": (200, 300),
                        "hora_baja": (75, 175)
                    },
                    "nombre": "Tanque 95 (Ficticio)"
                },
                {
                    "id": 3, 
                    "capacidad": 15000,
                    "consumo_base": {
                        "hora_pico": (350, 500),
                        "hora_normal": (250, 350),
                        "hora_baja": (100, 200)
                    },
                    "nombre": "Tanque diesel (Ficticio)"
                }
            ]

            fecha_final = datetime.now()
            fecha_inicial = fecha_final - timedelta(days=270)

            def get_hora_tipo(hora, dia_semana):
                """Determina el tipo de hora basado en el momento del día y día de la semana"""
                if dia_semana < 5:  # Días laborables
                    if hora in [7, 8, 9, 17, 18, 19]:  # Horas pico laborables
                        return "hora_pico"
                    elif hora in [23, 0, 1, 2, 3, 4, 5]:  # Horas bajas
                        return "hora_baja"
                    else:
                        return "hora_normal"
                else:  # Fines de semana
                    if hora in [10, 11, 12, 16, 17, 18]:  # Horas pico fin de semana
                        return "hora_pico"
                    elif hora in [0, 1, 2, 3, 4, 5]:  # Horas bajas
                        return "hora_baja"
                    else:
                        return "hora_normal"

            def generar_eventos_especiales():
                """Genera eventos aleatorios que afectan el consumo"""
                return {
                    'fecha': fecha_inicial + timedelta(days=random.randint(0, 270)),
                    'duracion': timedelta(hours=random.randint(2, 8)),
                    'factor': random.uniform(1.3, 1.8)  # Aumenta el consumo entre 30% y 80%
                }

            # Generar algunos eventos especiales (feriados, eventos locales, etc.)
            eventos_especiales = [generar_eventos_especiales() for _ in range(15)]

            for tanque_data in tanques:
                tanque = Tanque.objects.get(id=tanque_data["id"])
                volumen_actual = tanque_data["capacidad"] * random.uniform(0.7, 0.9)
                lecturas = []

                # Generar perturbaciones aleatorias usando ruido browniano
                dias_total = (fecha_final - fecha_inicial).days
                noise = np.random.normal(0, 0.15, dias_total * 24 * 60)  # Ruido por minuto
                
                fecha_actual = fecha_inicial
                idx_noise = 0

                while fecha_actual <= fecha_final:
                    # Factores base
                    hora_tipo = get_hora_tipo(fecha_actual.hour, fecha_actual.weekday())
                    consumo_base_rango = tanque_data["consumo_base"][hora_tipo]
                    
                    # Factor de evento especial
                    factor_evento = 1.0
                    for evento in eventos_especiales:
                        if evento['fecha'] <= fecha_actual <= evento['fecha'] + evento['duracion']:
                            factor_evento = evento['factor']
                            break

                    # Calcular consumo por minuto con variaciones
                    consumo_base = random.uniform(*consumo_base_rango) / 60
                    factor_estacional = 1.0
                    
                    # Ajustes estacionales más pronunciados
                    mes = fecha_actual.month
                    if tanque_data["nombre"] == "Diesel":
                        if mes in [6, 7, 8]:  # Invierno
                            factor_estacional = random.uniform(1.3, 1.5)
                        elif mes in [12, 1, 2]:  # Verano
                            factor_estacional = random.uniform(0.7, 0.9)
                    else:  # Bencinas
                        if mes in [12, 1, 2]:  # Verano
                            factor_estacional = random.uniform(1.2, 1.4)
                        elif mes in [6, 7, 8]:  # Invierno
                            factor_estacional = random.uniform(0.8, 0.9)

                    # Aplicar ruido y factores
                    consumo_final = (
                        consumo_base 
                        * factor_estacional 
                        * factor_evento 
                        * (1 + noise[idx_noise])  # Ruido browniano
                    )

                    # Reducir volumen
                    volumen_actual -= max(0, consumo_final)

                    # Simular reabastecimientos más realistas
                    if volumen_actual <= tanque_data["capacidad"] * random.uniform(0.15, 0.25):
                        # Simular tiempo de recarga
                        fecha_actual += timedelta(minutes=random.randint(30, 60))
                        volumen_actual = tanque_data["capacidad"] * random.uniform(0.95, 0.98)

                    nivel = (volumen_actual / tanque_data["capacidad"]) * 100

                    # Agregar algo de ruido a las mediciones
                    nivel += random.uniform(-0.05, 0.05)
                    volumen_actual += random.uniform(-5, 5)

                    lecturas.append(
                        Lectura(
                            tanque=tanque,
                            fecha=fecha_actual,
                            nivel=round(max(0, min(100, nivel)), 2),
                            volumen=round(max(0, volumen_actual), 2),
                            temperatura=round(random.uniform(15, 35), 2),
                        )
                    )

                    fecha_actual += timedelta(minutes=1)
                    idx_noise = (idx_noise + 1) % len(noise)

                    if len(lecturas) >= 1000:
                        Lectura.objects.bulk_create(lecturas, batch_size=1000)
                        lecturas = []

                if lecturas:
                    Lectura.objects.bulk_create(lecturas, batch_size=1000)

            self.stdout.write(self.style.SUCCESS("¡Datos simulados generados exitosamente!"))

        except Exception as e:
            self.stderr.write(f"Error al generar datos simulados: {e}")