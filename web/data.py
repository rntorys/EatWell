"""Catálogo de demostración: cantidades para una persona y precios ficticios en CLP.

El precio de cada ingrediente corresponde a UN gramo, mililitro o unidad.
Se estima el costo de las cantidades usadas, no el de envases completos.
Todas las recetas rinden una porción. Los pesos de arroz, pasta y legumbres
corresponden al producto seco; los demás, a la cantidad antes de cocinar.
"""

INGREDIENTES = {
    "avena": {"nombre": "Avena", "unidad": "g", "precio": 2},
    "leche": {"nombre": "Leche", "unidad": "ml", "precio": 1},
    "platano": {"nombre": "Plátano", "unidad": "g", "precio": 2},
    "pan": {"nombre": "Pan integral", "unidad": "g", "precio": 3},
    "huevo": {"nombre": "Huevos", "unidad": "unidad", "precio": 250},
    "arroz": {"nombre": "Arroz", "unidad": "g", "precio": 2},
    "lentejas": {"nombre": "Lentejas", "unidad": "g", "precio": 3},
    "fideos": {"nombre": "Fideos", "unidad": "g", "precio": 2},
    "pollo": {"nombre": "Pollo", "unidad": "g", "precio": 5},
    "atun": {"nombre": "Atún (lata individual)", "unidad": "unidad", "precio": 1200},
    "papa": {"nombre": "Papas", "unidad": "g", "precio": 1},
    "zanahoria": {"nombre": "Zanahorias", "unidad": "g", "precio": 1},
    "tomate": {"nombre": "Tomates", "unidad": "g", "precio": 2},
    "cebolla": {"nombre": "Cebollas", "unidad": "g", "precio": 1},
    "aceite": {"nombre": "Aceite", "unidad": "ml", "precio": 3},
    "sal": {"nombre": "Sal", "unidad": "g", "precio": 1},
}

RECETAS = [
    {
        "nombre": "Avena con leche y plátano",
        "tipo": "desayuno",
        "porciones": 1,
        "ingredientes": {"avena": 60, "leche": 200, "platano": 100},
    },
    {
        "nombre": "Pan integral con huevo",
        "tipo": "desayuno",
        "porciones": 1,
        "ingredientes": {"pan": 100, "huevo": 1, "aceite": 5},
    },
    {
        "nombre": "Pan integral con plátano y leche",
        "tipo": "desayuno",
        "porciones": 1,
        "ingredientes": {"pan": 80, "platano": 100, "leche": 200},
    },
    {
        "nombre": "Lentejas con arroz",
        "tipo": "almuerzo",
        "porciones": 1,
        "ingredientes": {
            "lentejas": 90, "arroz": 60, "zanahoria": 60,
            "cebolla": 40, "aceite": 5, "sal": 1,
        },
    },
    {
        "nombre": "Pollo con arroz y verduras",
        "tipo": "almuerzo",
        "porciones": 1,
        "ingredientes": {
            "pollo": 150, "arroz": 80, "zanahoria": 80,
            "cebolla": 40, "aceite": 5, "sal": 1,
        },
    },
    {
        "nombre": "Fideos con atún y tomate",
        "tipo": "almuerzo",
        "porciones": 1,
        "ingredientes": {
            "fideos": 100, "atun": 1, "tomate": 150,
            "cebolla": 30, "aceite": 5, "sal": 1,
        },
    },
    {
        "nombre": "Tortilla de papas con tomate",
        "tipo": "almuerzo",
        "porciones": 1,
        "ingredientes": {
            "papa": 250, "huevo": 2, "tomate": 100,
            "cebolla": 40, "aceite": 10, "sal": 1,
        },
    },
    {
        "nombre": "Sopa de verduras con pan",
        "tipo": "cena",
        "porciones": 1,
        "ingredientes": {
            "papa": 200, "zanahoria": 100, "cebolla": 50,
            "pan": 60, "aceite": 5, "sal": 1,
        },
    },
    {
        "nombre": "Ensalada de lentejas con huevo",
        "tipo": "cena",
        "porciones": 1,
        "ingredientes": {
            "lentejas": 70, "huevo": 1, "tomate": 100,
            "zanahoria": 60, "aceite": 5, "sal": 1,
        },
    },
    {
        "nombre": "Sándwich de pollo y tomate",
        "tipo": "cena",
        "porciones": 1,
        "ingredientes": {
            "pan": 100, "pollo": 100, "tomate": 100, "aceite": 5, "sal": 1,
        },
    },
    {
        "nombre": "Arroz salteado con huevo y verduras",
        "tipo": "cena",
        "porciones": 1,
        "ingredientes": {
            "arroz": 80, "huevo": 2, "zanahoria": 80,
            "cebolla": 40, "aceite": 5, "sal": 1,
        },
    },
]

# Más opciones del catálogo de EatWell (ODEPA aporta precios, no recetas).
# Todas las cantidades corresponden a una porción.
RECETAS.extend([
    {"nombre": "Avena caliente con leche", "tipo": "desayuno", "porciones": 1,
     "ingredientes": {"avena": 80, "leche": 300}},
    {"nombre": "Pan con tomate y huevo", "tipo": "desayuno", "porciones": 1,
     "ingredientes": {"pan": 100, "tomate": 100, "huevo": 1, "aceite": 5}},
    {"nombre": "Tortitas de avena y plátano", "tipo": "desayuno", "porciones": 1,
     "ingredientes": {"avena": 60, "platano": 100, "huevo": 1, "leche": 50, "aceite": 5}},
    {"nombre": "Huevos revueltos con pan integral", "tipo": "desayuno", "porciones": 1,
     "ingredientes": {"huevo": 2, "pan": 80, "leche": 30, "aceite": 5, "sal": 1}},
    {"nombre": "Avena remojada con plátano", "tipo": "desayuno", "porciones": 1,
     "ingredientes": {"avena": 70, "leche": 250, "platano": 120}},
    {"nombre": "Tostadas con tomate y leche", "tipo": "desayuno", "porciones": 1,
     "ingredientes": {"pan": 100, "tomate": 120, "leche": 200, "aceite": 5}},
    {"nombre": "Omelette de tomate con pan", "tipo": "desayuno", "porciones": 1,
     "ingredientes": {"huevo": 2, "tomate": 100, "pan": 60, "aceite": 5, "sal": 1}},
    {"nombre": "Pan con huevo duro y plátano", "tipo": "desayuno", "porciones": 1,
     "ingredientes": {"pan": 80, "huevo": 1, "platano": 100}},
    {"nombre": "Arroz con pollo y tomate", "tipo": "almuerzo", "porciones": 1,
     "ingredientes": {"arroz": 90, "pollo": 150, "tomate": 100, "cebolla": 40, "aceite": 5, "sal": 1}},
    {"nombre": "Guiso de lentejas con papas", "tipo": "almuerzo", "porciones": 1,
     "ingredientes": {"lentejas": 100, "papa": 200, "zanahoria": 80, "cebolla": 50, "aceite": 5, "sal": 1}},
    {"nombre": "Fideos con pollo y verduras", "tipo": "almuerzo", "porciones": 1,
     "ingredientes": {"fideos": 100, "pollo": 130, "zanahoria": 80, "cebolla": 40, "aceite": 5, "sal": 1}},
    {"nombre": "Papas cocidas con atún y tomate", "tipo": "almuerzo", "porciones": 1,
     "ingredientes": {"papa": 300, "atun": 1, "tomate": 150, "aceite": 5, "sal": 1}},
    {"nombre": "Arroz con lentejas y huevo", "tipo": "almuerzo", "porciones": 1,
     "ingredientes": {"arroz": 70, "lentejas": 80, "huevo": 1, "cebolla": 40, "aceite": 5, "sal": 1}},
    {"nombre": "Pollo con puré de papas", "tipo": "almuerzo", "porciones": 1,
     "ingredientes": {"pollo": 150, "papa": 300, "leche": 100, "aceite": 5, "sal": 1}},
    {"nombre": "Fideos con salsa de lentejas", "tipo": "almuerzo", "porciones": 1,
     "ingredientes": {"fideos": 90, "lentejas": 80, "tomate": 150, "cebolla": 50, "aceite": 5, "sal": 1}},
    {"nombre": "Tortilla de zanahoria con arroz", "tipo": "almuerzo", "porciones": 1,
     "ingredientes": {"huevo": 2, "zanahoria": 150, "arroz": 80, "cebolla": 30, "aceite": 10, "sal": 1}},
    {"nombre": "Crema de zanahoria con tostadas", "tipo": "cena", "porciones": 1,
     "ingredientes": {"zanahoria": 200, "papa": 150, "leche": 100, "pan": 60, "sal": 1}},
    {"nombre": "Ensalada de arroz con atún", "tipo": "cena", "porciones": 1,
     "ingredientes": {"arroz": 80, "atun": 1, "tomate": 100, "zanahoria": 80, "aceite": 5}},
    {"nombre": "Sándwich de huevo y tomate", "tipo": "cena", "porciones": 1,
     "ingredientes": {"pan": 100, "huevo": 2, "tomate": 100, "sal": 1}},
    {"nombre": "Sopa de pollo con fideos", "tipo": "cena", "porciones": 1,
     "ingredientes": {"pollo": 100, "fideos": 60, "zanahoria": 100, "cebolla": 40, "sal": 1}},
    {"nombre": "Tortilla de lentejas con tomate", "tipo": "cena", "porciones": 1,
     "ingredientes": {"lentejas": 80, "huevo": 1, "tomate": 150, "cebolla": 30, "aceite": 5, "sal": 1}},
    {"nombre": "Ensalada de papas con huevo", "tipo": "cena", "porciones": 1,
     "ingredientes": {"papa": 250, "huevo": 2, "zanahoria": 80, "aceite": 5, "sal": 1}},
    {"nombre": "Pollo salteado con verduras y pan", "tipo": "cena", "porciones": 1,
     "ingredientes": {"pollo": 120, "zanahoria": 120, "cebolla": 60, "pan": 60, "aceite": 5, "sal": 1}},
    {"nombre": "Tostadas con pasta de lentejas y tomate", "tipo": "cena", "porciones": 1,
     "ingredientes": {"pan": 100, "lentejas": 80, "tomate": 100, "aceite": 5, "sal": 1}},
])
