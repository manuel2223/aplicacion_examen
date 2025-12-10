import streamlit as st
import json
import random
import re

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Examen CSI", page_icon="📝")

# --- CARGAR PREGUNTAS ---
@st.cache_data # Esto hace que cargue rápido y no lea el archivo a cada rato
def cargar_preguntas():
    try:
        with open("preguntas_csi.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("No se encontró el archivo preguntas_csi.json")
        return []

preguntas = cargar_preguntas()

# --- GESTIÓN DEL ESTADO (MEMORIA DEL USUARIO) ---
# En web, cada vez que tocas un botón, el script se reinicia.
# session_state sirve para recordar cosas entre clics.

if 'examen_iniciado' not in st.session_state:
    st.session_state.examen_iniciado = False
if 'preguntas_actuales' not in st.session_state:
    st.session_state.preguntas_actuales = []
if 'indice' not in st.session_state:
    st.session_state.indice = 0
if 'aciertos' not in st.session_state:
    st.session_state.aciertos = 0
if 'falladas_sesion' not in st.session_state:
    st.session_state.falladas_sesion = []
if 'mostrar_resultado' not in st.session_state:
    st.session_state.mostrar_resultado = False
if 'mensaje_resultado' not in st.session_state:
    st.session_state.mensaje_resultado = ""

# --- FUNCIONES ---

def iniciar_examen(lista_preguntas):
    st.session_state.preguntas_actuales = lista_preguntas[:]
    random.shuffle(st.session_state.preguntas_actuales)
    st.session_state.indice = 0
    st.session_state.aciertos = 0
    st.session_state.mostrar_resultado = False
    st.session_state.examen_iniciado = True
    st.rerun() # Recarga la página para mostrar la primera pregunta

def verificar_respuesta(pregunta, respuesta_usuario):
    es_correcta = False
    mensaje = ""
    
    if pregunta["tipo"] == "test":
        # respuesta_usuario es el índice (0, 1, 2...)
        letra_correcta = pregunta["respuesta"]
        idx_correcto = ord(letra_correcta) - ord('a')
        
        if respuesta_usuario == idx_correcto:
            es_correcta = True
            mensaje = "✅ ¡Correcto!"
        else:
            texto_correcto = pregunta['opciones'][idx_correcto]
            mensaje = f"❌ Incorrecto. La correcta era la {letra_correcta}) {texto_correcto}"

    elif pregunta["tipo"] == "corchetes":
        correctas = [c.strip() for c in pregunta["respuesta"]]
        usuario = [u.strip() for u in respuesta_usuario]
        
        if usuario == correctas:
            es_correcta = True
            mensaje = "✅ ¡Correcto!"
        else:
            mensaje = f"❌ Incorrecto. Solución: {', '.join(correctas)}"

    # Guardar resultado y avanzar
    if es_correcta:
        st.session_state.aciertos += 1
    else:
        st.session_state.falladas_sesion.append(pregunta)
    
    st.session_state.mensaje_resultado = mensaje
    st.session_state.mostrar_resultado = True
    st.rerun()

def siguiente_pregunta():
    st.session_state.indice += 1
    st.session_state.mostrar_resultado = False
    st.rerun()

def volver_menu():
    st.session_state.examen_iniciado = False
    st.rerun()

# --- INTERFAZ GRÁFICA (LO QUE SE VE) ---

st.title("Sistema de Examen Online")

if not st.session_state.examen_iniciado:
    # --- MENÚ PRINCIPAL ---
    st.header("Menú Principal")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📝 Hacer todas las preguntas", use_container_width=True):
            iniciar_examen(preguntas)
            
    with col2:
        temas = sorted(set(p.get("tema", 0) for p in preguntas))
        tema_selec = st.selectbox("Filtrar por tema:", temas)
        if st.button("📂 Iniciar por tema", use_container_width=True):
            preguntas_tema = [p for p in preguntas if p.get("tema", 0) == tema_selec]
            iniciar_examen(preguntas_tema)

    if st.session_state.falladas_sesion:
        st.warning(f"Has fallado {len(st.session_state.falladas_sesion)} preguntas en esta sesión.")
        if st.button("Repasar falladas de esta sesión"):
            iniciar_examen(st.session_state.falladas_sesion)

else:
    # --- PANTALLA DE EXAMEN ---
    
    # Verificar si terminamos
    if st.session_state.indice >= len(st.session_state.preguntas_actuales):
        st.success(f"🎉 ¡Examen finalizado!")
        st.metric("Puntuación Final", f"{st.session_state.aciertos} / {len(st.session_state.preguntas_actuales)}")
        if st.button("Volver al menú"):
            volver_menu()
    
    else:
        # Mostrar pregunta actual
        pregunta = st.session_state.preguntas_actuales[st.session_state.indice]
        st.progress((st.session_state.indice) / len(st.session_state.preguntas_actuales))
        st.subheader(f"Pregunta {st.session_state.indice + 1}")
        st.write(pregunta["texto"])
        
        # --- Lógica de visualización por tipo ---
        
        if not st.session_state.mostrar_resultado:
            # MOSTRAR OPCIONES PARA RESPONDER
            
            if pregunta["tipo"] == "test":
                opciones = pregunta["opciones"]
                # Usamos radio button. El índice de la selección será la respuesta
                # Truco: mostramos opciones pero internamente usamos el indice
                opcion_elegida = st.radio("Selecciona una opción:", opciones, index=None)
                
                if st.button("Comprobar Respuesta", type="primary"):
                    if opcion_elegida:
                        idx_respuesta = opciones.index(opcion_elegida)
                        verificar_respuesta(pregunta, idx_respuesta)
                    else:
                        st.warning("Selecciona una opción primero")

            elif pregunta["tipo"] == "corchetes":
                grupos = re.findall(r'\[([^\]]+)\]', pregunta["texto"])
                respuestas_usuario = []
                
                st.write("Selecciona la palabra correcta para cada hueco:")
                
                todos_seleccionados = True
                for i, grupo in enumerate(grupos):
                    opciones = [op.strip() for op in grupo.split("|")]
                    random.shuffle(opciones)
                    seleccion = st.selectbox(f"Hueco {i+1}:", ["..."] + opciones, key=f"g_{st.session_state.indice}_{i}")
                    if seleccion == "...":
                        todos_seleccionados = False
                    respuestas_usuario.append(seleccion)
                
                if st.button("Comprobar Respuesta", type="primary"):
                    if todos_seleccionados:
                        verificar_respuesta(pregunta, respuestas_usuario)
                    else:
                        st.warning("Rellena todos los huecos")

        else:
            # MOSTRAR RESULTADO Y BOTÓN SIGUIENTE
            if "✅" in st.session_state.mensaje_resultado:
                st.success(st.session_state.mensaje_resultado)
            else:
                st.error(st.session_state.mensaje_resultado)
            
            if st.button("Siguiente Pregunta ➡"):
                siguiente_pregunta()