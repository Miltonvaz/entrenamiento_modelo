import os
import csv
import random

# Seed for reproducibility
random.seed(123)

# ==========================================
# CONVERSATIONAL INJECTIONS (The "Teacher's Style")
# ==========================================

self_corrections = [
    "o sea no espérense, mejor así",
    "digo, mejor dicho",
    "bueno no, miento, en realidad",
    "espera, me equivoqué de signo, es",
    "bueno o sea sí, pero más fácil",
    "o sea, dejen borro esto, en verdad es"
]

visual_references = [
    "como ven aquí en el ejemplo",
    "miren esta parte del diagrama",
    "en la diapositiva anterior vimos que",
    "si observan la gráfica en la pizarra",
    "aquí en el proyector les muestro cómo",
    "en este dibujo de la derecha"
]

comparations = [
    "esto es idéntico a cuando",
    "imagínense que es como",
    "piénsenlo como si fuera un",
    "es el mismo principio que cuando",
    "hagan de cuenta que es como cuando"
]

rhetorical_questions = [
    "¿por qué pasa esto? pues porque",
    "¿qué significa esto? básicamente que",
    "¿cómo llegamos a esto? pues resulta que",
    "¿dónde se aplica esto? lo vemos cuando"
]

cut_offs = [
    "entonces si... a ver retrocedo, primero",
    "si tenemos esto... bueno, volviendo a lo de antes",
    "y luego calculamos... esperen, me salté un paso",
    "a ver, dejen me organizo, lo que pasa es que"
]

# Helper to inject speech patterns randomly into templates
def inject_conversational(phrase):
    choice = random.random()
    if choice < 0.15:
        # Prefix
        pattern = random.choice(self_corrections + cut_offs)
        return f"{pattern} {phrase}"
    elif choice < 0.30:
        # Infix (insert after first clause)
        pattern = random.choice(visual_references + comparations)
        words = phrase.split()
        if len(words) > 4:
            mid = len(words) // 2
            return f"{' '.join(words[:mid])} {pattern} {' '.join(words[mid:])}"
    elif choice < 0.45:
        # Suffix
        pattern = random.choice(rhetorical_questions)
        return f"{phrase} {pattern} bueno, así funciona"
    return phrase

# ==========================================
# VOCABULARY BY SUBJECT (With intentional overlaps)
# ==========================================

math_vars = ["x", "y", "z", "t", "n", "theta", "alpha", "f(x)", "u"]
math_operators = ["derivada", "integral", "limite", "sumatoria", "raiz cuadrada", "determinante", "jacobiano"]
math_concepts = ["numero complejo", "ecuacion diferencial", "matriz identidad", "funcion continua", "vector ortogonal", "teorema del valor medio"]

# Shared vocabulary between Math and Physics
shared_stem = ["vector", "velocidad", "aceleracion", "constante", "derivada respecto al tiempo", "ecuacion diferencial", "intervalo", "grafica", "limite", "derivada parcial"]

phys_vars = ["masa", "fuerza", "torque", "gravedad", "voltaje", "corriente", "densidad", "potencia", "momento lineal"]
phys_concepts = ["segunda ley de newton", "energia cinetica", "choque elastico", "campo magnetico", "friccion estatica", "equilibrio termodinamico"]

chem_concepts = ["enlace covalente", "concentracion molar", "reactivo limitante", "constante de equilibrio", "configuracion electronica", "ph de la solucion", "reaccion redox"]
chem_terms = ["octeto", "acido clorhidrico", "electrolito", "catalizador", "isomeros", "destilacion", "masa molecular", "disolvente"]

bio_concepts = ["membrana celular", "doble helice de adn", "fotosintesis en cloroplastos", "mitosis celular", "seleccion natural de darwin", "homeostasis corporal", "sintesis de proteinas"]
bio_terms = ["mitocondria", "ribosoma", "arn mensajero", "meiosis", "celula procariota", "sinapsis neuronal", "enzimas", "ciclo de krebs", "fenotipo"]

prog_concepts = ["ciclo for", "puntero nulo", "funcion recursiva", "complejidad logaritmica", "recolector de basura", "inyeccion de dependencias", "prueba unitaria"]
prog_terms = ["segmentation fault", "variable entera", "bloque else", "lista enlazada", "error de sintaxis", "api rest", "git push", "estructura pila"]

gen_actions = ["entregar la tarea", "apagar los telefonos", "hacer una pausa", "revisar las rubricas", "hacer equipos", "firmar la asistencia"]
gen_admin = ["examen parcial", "laboratorio de mañana", "matricula escolar", "justificante medico", "junta de consejo", "plataforma escolar"]

# ==========================================
# PROCEDURAL TEMPLATES (15-20 structures per class with cross-overlap)
# ==========================================

def get_math_samples():
    v1 = random.choice(math_vars)
    v2 = random.choice([v for v in math_vars if v != v1])
    op = random.choice(math_operators)
    concept = random.choice(math_concepts)
    shared = random.choice(shared_stem)
    num = str(random.randint(0, 10))
    
    templates = [
        f"para calcular la {op} de {v1} respecto a {v2} tenemos que aplicar la regla de la cadena",
        f"este... si tenemos que {v1} es una {concept} entonces su integral no es trivial",
        f"miren la pizarra si evaluamos el {op} de esta ecuacion cuando tiende a {num} da cero",
        f"a ver multipliquen la {concept} por la {op} de {v1} y vean qué pasa",
        f"la matriz de coeficientes asociada a este {concept} es simetrica",
        f"si derivamos esta {concept} con respecto al parametro {v2} nos da un {shared}",
        f"la sumatoria de {v1} desde uno hasta infinito converge si el {op} es menor que uno",
        f"este... imagínense que {v1} es un {concept} y lo graficamos en coordenadas polares",
        f"¿cómo resolvemos este sistema de ecuaciones? aplicando el {concept} en cada renglon",
        f"la {op} de esta funcion es positiva en todo el intervalo lo que significa que crece",
        f"este... el discriminante de la {concept} nos dice si las raices son reales",
        f"si hacemos un cambio de variable donde u es igual a {v1} al cuadrado la integral se simplifica",
        f"a ver dibujen el plano cartesiano y localicen el {concept}",
        f"¿por qué el {op} da indeterminado? pues porque estamos dividiendo entre cero",
        f"el teorema nos garantiza que para toda {concept} existe un punto donde la derivada vale cero",
        f"este... si {v1} y {v2} son ortogonales su producto punto es cero",
        f"para esta {concept} lineal de primer orden usamos un factor integrante",
        f"la proyeccion de este {shared} sobre el plano nos da una {concept}",
        f"el area bajo la curva se calcula haciendo la {op} definida en estos limites",
        f"si aplicamos la transformada a esta {concept} pasamos al dominio de la frecuencia",
        # Overlapping math templates simulating physics lectures
        f"la aceleracion es una {op} de la velocidad con respecto al tiempo",
        f"si el {shared} de posicion es constante entonces su derivada respecto al tiempo vale cero",
        f"en el analisis de este movimiento rectilineo planteamos una {concept}",
        f"este... la grafica nos muestra que en el intervalo dado la funcion es continua",
        f"calculamos el {shared} cruz entre la fuerza y la distancia para ver el momento"
    ]
    return templates

def get_phys_samples():
    v = random.choice(phys_vars)
    concept = random.choice(phys_concepts)
    shared = random.choice(shared_stem)
    num = str(random.randint(1, 100))
    
    templates = [
        f"si el objeto parte del reposo su {v} inicial es cero pero tiene una {shared} constante",
        f"la fuerza de friccion se opone al movimiento y depende de la {concept}",
        f"calculamos el {shared} multiplicando la constante por la masa en esta formula",
        f"este... imagínense que esta barra gira y produce un {v} sobre el eje de rotacion",
        f"la corriente electromagnetica genera un campo y eso altera la {v}",
        f"en un choque elastico recuerden que se conserva la {concept}",
        f"la caida libre es un movimiento rectilineo donde la unica fuerza es la {v}",
        f"si conectamos las resistencias en paralelo la {v} es la misma pero el amperaje cambia",
        f"¿por qué no se mueve la caja? pues porque la {concept} compensa la fuerza aplicada",
        f"el rozamiento del aire frena al proyectil o sea la {v} no se mantiene constante",
        f"la ley de conservacion nos dice que la {concept} total del sistema permanece igual",
        f"si la masa aumenta al doble la {v} se reduce a la mitad para mantener el momento constante",
        f"esta ley relaciona la presion y la temperatura en un {concept}",
        f"el periodo de oscilacion de este oscilador depende de la masa y de la constante del resorte",
        f"a ver miren la {shared} la flecha representa el vector de {v} apuntando hacia el centro",
        f"la potencia electrica disipada por este circuito es proporcional al cuadrado de la {v}",
        f"este... el torque neto es la suma de todas las fuerzas multiplicadas por su brazo de palanca",
        f"la densidad del objeto es menor que la del agua por eso experimenta un {shared} hacia arriba",
        f"la ley de coulomb determina la atraccion entre estas cargas a una distancia de {num} centimetros",
        f"si el sistema llega al {concept} la transferencia de calor neta es cero",
        # Math heavy physics templates
        f"planteamos la ecuacion diferencial para la posicion de la particula en el {shared}",
        f"la velocidad se obtiene haciendo la integral de la aceleracion respecto al tiempo",
        f"el limite de la velocidad cuando el tiempo tiende a infinito nos da la velocidad terminal",
        f"la derivada de la energia respecto al tiempo nos entrega la potencia instantanea del sistema",
        f"para calcular el trabajo total integramos la fuerza a lo largo de este intervalo"
    ]
    return templates


def get_chem_samples():
    concept = random.choice(chem_concepts)
    term = random.choice(chem_terms)
    num = str(random.randint(1, 14))
    
    templates = [
        f"este... en el {concept} los atomos comparten electrones para alcanzar estabilidad",
        f"calculen la {concept} disolviendo diez gramos de soluto en el matraz",
        f"para balancear esta reaccion redox el {term} debe perder electrones",
        f"el ph de la solucion nos dio {num} lo que significa que es una sustancia alcalina",
        f"este... si agregamos un {term} la velocidad de la reaccion aumenta porque baja la energia",
        f"los {term} tienen la misma formula quimica pero su estructura espacial es diferente",
        f"la entalpia de esta reaccion es negativa lo que nos indica un proceso {concept}",
        f"a ver separamos el alcohol del agua usando el metodo de {term} por puntos de ebullicion",
        f"la configuracion electronica del elemento termina en el subnivel s y tiene valencia {num}",
        f"el agua funciona como {term} polar disolviendo la sal de mesa",
        f"este... la estequiometria nos permite calcular el rendimiento teorico a partir de la {concept}",
        f"¿qué pasa si la {concept} es muy alta? la reaccion se desplaza hacia la izquierda",
        f"la masa molecular del compuesto es de cincuenta gramos por mol segun la tabla periodica",
        f"en el enlace covalente el nitrogeno comparte electrones para llenar su {term}",
        f"este... el acido clorhidrico es un electrolito fuerte que se ioniza completamente",
        f"la ley de gases ideales asume que las moleculas del {term} no interactuan entre si",
        f"si calentamos la solucion la solubilidad de este soluto solido va a aumentar",
        f"la electronegatividad de este elemento es muy alta por eso atrae con fuerza los electrones",
        f"en la celda galvanica la oxidacion ocurre en el anodo debido a la {concept}",
        f"este... miren el diagrama el tubo de ensayo muestra la precipitacion del {term}"
    ]
    return templates

def get_bio_samples():
    concept = random.choice(bio_concepts)
    term = random.choice(bio_terms)
    
    templates = [
        f"la {concept} controla la entrada de nutrientes mediante transporte activo y pasivo",
        f"el adn contiene la informacion genetica organizada en una estructura de {concept}",
        f"este... la fotosintesis transforma dioxido de carbono y agua en glucosa usando la {term}",
        f"durante la {term} el huso mitotico separa las cromatidas hermanas hacia los polos",
        f"la seleccion natural favorece a los organismos que mejor se adaptan al {term}",
        f"las mitocondrias son los organelos donde ocurre la respiracion celular y la produccion de {term}",
        f"los ribosomas traducen el {term} para ensamblar las proteinas",
        f"a ver las bacterias no tienen organelos delimitados porque son {concept}",
        f"la homeostasis mantiene constante la temperatura corporal a pesar del frio externo",
        f"este... la sinapsis es la transmision de neurotransmisores entre dos celulas de la {term}",
        f"las enzimas actuan como biocatalizadores acelerando las reacciones quimicas en la {term}",
        f"el ciclo de krebs es una ruta metabolica clave que tiene lugar en la {term}",
        f"durante la meiosis se reduce a la mitad el numero de cromosomas para formar la {term}",
        f"la celula vegetal tiene pared celular de celulosa y una gran vacuola central",
        f"el arn de transferencia lleva los aminoacidos al ribosoma durante la {concept}",
        f"las celulas eucariotas si tienen un nucleo definido que contiene el material de {term}",
        f"la reproduccion asexual produce clones exactos del progenitor sin variacion de {term}",
        f"el fenotipo es la manifestacion visible de la carga genetica del individuo",
        f"este... los virus necesitan de la maquinaria celular para replicar su {term}",
        f"miren el esquema el citoesqueleto mantiene la forma de la celula y organiza la {term}"
    ]
    return templates

def get_prog_samples():
    concept = random.choice(prog_concepts)
    term = random.choice(prog_terms)
    
    templates = [
        f"este... usamos un {concept} para iterar sobre los elementos del vector y sumarlos",
        f"el programa lanzo un {term} porque intentamos acceder a una direccion de memoria invalida",
        f"esta funcion recursiva debe tener un caso base para evitar el desbordamiento de pila",
        f"declaramos una {term} fuera del metodo para que tenga alcance global en la clase",
        f"la complejidad de tiempo de este algoritmo de busqueda es {concept}",
        f"si la condicion del if se cumple entra al bloque principal si no ejecuta el {term}",
        f"el recolector de basura se encarga de liberar la memoria de objetos huerfanos",
        f"a ver miren el codigo esta clase hereda los atributos y extiende el comportamiento de {term}",
        f"vamos a depurar el codigo para ver el estado de las variables en este {concept}",
        f"la base de datos rechazo la consulta porque habia un {term} en la sintaxis sql",
        f"este... la lista enlazada es mas eficiente que el arreglo para inserciones frecuentes",
        f"el compilador da un error porque falta un punto y coma al final de esta {term}",
        f"esta api rest responde con un objeto json que contiene los datos de usuario",
        f"si usamos programacion asincrona evitamos que la interfaz del hilo principal se congele",
        f"este... encapsulamos los campos privados de la clase usando metodos de acceso de {term}",
        f"la prueba unitaria fallo porque el valor retornado no coincide con el esperado",
        f"usamos inyeccion de dependencias para que el modulo no dependa directamente del {term}",
        f"si el indice de la matriz supera el tamaño maximo tendremos una excepcion de {term}",
        f"hacemos un commit de los cambios y luego un {term} al servidor de desarrollo",
        f"este... el funcionamiento de la pila sigue la regla de {concept}"
    ]
    return templates

def get_gen_samples():
    action = random.choice(gen_actions)
    admin = random.choice(gen_admin)
    time = f"{random.randint(1, 12)}:00"
    
    templates = [
        f"a ver chicos recuerden que tienen que {action} en la plataforma antes del viernes",
        f"este... apaguen sus celulares para evitar ruidos molestos durante el {admin}",
        f"bueno hagamos una pausa de diez minutos para estirar las piernas y tomar aire",
        f"la rubrica del proyecto final ya esta disponible en la {admin}",
        f"¿alguien tiene alguna duda sobre el calendario de examenes o todo esta claro?",
        f"este... organicense en grupos de tres personas para trabajar en el {admin}",
        f"si no han firmado la hoja de asistencia por favor pasen al escritorio al final",
        f"las diapositivas y lecturas de la sesion se las voy a compartir en el {admin}",
        f"muchachos mantengan el orden y el silencio que sus compañeros estan exponiendo",
        f"el examen parcial equivale al treinta por ciento de la calificacion ordinaria",
        f"este... lean con cuidado las instrucciones antes de subir el archivo pdf",
        f"mañana la clase sera virtual debido a una reunion de {admin}",
        f"si tienen inconvenientes con la matricula acudan al edificio de control escolar",
        f"bueno muchachos vamos a comenzar tomando lista de los presentes de hoy",
        f"la sesion de practica se cancela porque el material del {admin} no llego a tiempo",
        f"este... recuerden traer su justificante medico si faltaron a la sesion del lunes",
        f"formen sus equipos de trabajo y registrenlos en la hoja de calculo antes de las {time}",
        f"alcen la mano quienes todavia no tienen tema asignado para la exposicion",
        f"bueno por hoy terminamos la clase pueden retirarse y que tengan buen dia",
        f"este... la lectura del capitulo dos es obligatoria para la evaluacion del {admin}"
    ]
    return templates

# ==========================================
# CORPUS GENERATION LOOP (180 per subject)
# ==========================================

subjects = {
    "matematicas": get_math_samples,
    "fisica": get_phys_samples,
    "quimica": get_chem_samples,
    "biologia": get_bio_samples,
    "programacion": get_prog_samples,
    "general": get_gen_samples
}

output_dir = os.path.join(os.path.dirname(__file__), "..", "data_mining")
os.makedirs(output_dir, exist_ok=True)
csv_path = os.path.join(output_dir, "corpus_materias.csv")

print("[GENERATOR] Creating high-variability classroom corpus...")

with open(csv_path, mode='w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["texto", "etiqueta"])
    
    counts = {s: 0 for s in subjects}
    
    for subject, generator_func in subjects.items():
        unique_phrases = set()
        
        # Keep generating until we hit exactly 180 unique samples
        attempts = 0
        while len(unique_phrases) < 180 and attempts < 10000:
            attempts += 1
            # Run generator function to get a batch of template strings
            templates = generator_func()
            # Select a random template
            raw_phrase = random.choice(templates)
            # Inject conversational styles randomly (self-corrections, visual references, etc.)
            phrase = inject_conversational(raw_phrase)
            
            # Clean duplicate whitespaces
            phrase = " ".join(phrase.split()).lower()
            
            unique_phrases.add(phrase)
            
        for phrase in unique_phrases:
            writer.writerow([phrase, subject])
            counts[subject] += 1

print(f"[GENERATOR] Success! Saved 1080 samples to {csv_path}")
for s, c in counts.items():
    print(f"  - {s}: {c} examples")
