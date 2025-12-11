import streamlit as st
import json
import random
import re

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Examen INE", page_icon="📝")

# --- CARGAR PREGUNTAS ---
@st.cache_data # Esto hace que cargue rápido y no lea el archivo a cada rato
def cargar_preguntas():
    try:
        with open("preguntas_ine.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("No se encontró el archivo preguntas_ine.json")
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
            # === AQUÍ ESTÁ EL CAMBIO IMPORTANTE: USAMOS UN FORMULARIO ===
            # El formulario evita que la página se recargue al seleccionar una opción
            with st.form(key=f"formulario_pregunta_{st.session_state.indice}"):
                
                respuesta_a_enviar = None
                tipo_envio = ""

                if pregunta["tipo"] == "test":
                    opciones = pregunta["opciones"]
                    # Mostramos opciones (radio buttons)
                    opcion_elegida = st.radio("Selecciona una opción:", opciones, index=None)
                    tipo_envio = "test"
                    respuesta_a_enviar = opcion_elegida

                elif pregunta["tipo"] == "corchetes":
                    grupos = re.findall(r'\[([^\]]+)\]', pregunta["texto"])
                    respuestas_usuario = []
                    
                    st.write("Selecciona la palabra correcta para cada hueco:")
                    
                    todos_seleccionados = True
                    # Usamos un seed temporal para que el shuffle sea estable dentro de la misma pregunta
                    # si se recargara, pero el form lo evita principalmente.
                    semilla_visual = st.session_state.indice * 100 
                    
                    for i, grupo in enumerate(grupos):
                        opciones = [op.strip() for op in grupo.split("|")]
                        # Mezclamos usando una semilla fija para esta pregunta para que no bailen las opciones
                        random.Random(semilla_visual + i).shuffle(opciones)
                        
                        seleccion = st.selectbox(f"Hueco {i+1}:", ["..."] + opciones, key=f"g_{st.session_state.indice}_{i}")
                        if seleccion == "...":
                            todos_seleccionados = False
                        respuestas_usuario.append(seleccion)
                    
                    tipo_envio = "corchetes"
                    if todos_seleccionados:
                        respuesta_a_enviar = respuestas_usuario
                    else:
                        respuesta_a_enviar = None

                # Botón de envío del formulario
                boton_enviar = st.form_submit_button("Comprobar Respuesta", type="primary")

            # === LÓGICA AL PULSAR EL BOTÓN DEL FORMULARIO ===
            if boton_enviar:
                if respuesta_a_enviar is not None:
                    if tipo_envio == "test":
                        idx_respuesta = pregunta["opciones"].index(respuesta_a_enviar)
                        verificar_respuesta(pregunta, idx_respuesta)
                    elif tipo_envio == "corchetes":
                        verificar_respuesta(pregunta, respuesta_a_enviar)
                else:
                    st.warning("⚠️ Por favor, completa todas las opciones antes de comprobar.")

        else:
            # MOSTRAR RESULTADO Y BOTÓN SIGUIENTE (Fuera del formulario)
            if "✅" in st.session_state.mensaje_resultado:
                st.success(st.session_state.mensaje_resultado)
            else:
                st.error(st.session_state.mensaje_resultado)
            
            if st.button("Siguiente Pregunta ➡"):
                siguiente_pregunta()