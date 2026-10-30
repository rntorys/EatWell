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
