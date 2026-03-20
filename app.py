import streamlit as st
import pandas as pd
import io
from happy_friday_organizer import HappyFridayOrganizer

st.set_page_config(layout="wide")
st.title("🎉 Happy Friday Organizer 🎉")

st.markdown("""
Esta aplicación te ayuda a organizar los grupos mensuales de Happy Friday para tu generación escolar, minimizando las repeticiones de pares de niñas a lo largo del año.

**Instrucciones:**
1.  Ingresa la lista de todas las niñas.
2.  Define el calendario de anfitrionas mes a mes.
3.  Haz clic en "Organizar Happy Friday" para generar los grupos y el reporte PDF.
""")

# --- Entrada de Niñas ---
st.header("1. Lista de Niñas")

girls_input_method = st.radio(
    "¿Cómo quieres ingresar la lista de niñas?",
    ("Escribir manualmente (separadas por comas)", "Subir archivo CSV"),
    key="girls_input_method"
)

all_girls = []
if girls_input_method == "Escribir manualmente (separadas por comas)":
    girls_text = st.text_area("Nombres de las niñas (separados por comas):", key="girls_text")
    if girls_text:
        all_girls = [g.strip() for g in girls_text.split(',') if g.strip()]
else: # Subir archivo CSV
    uploaded_girls_file = st.file_uploader("Sube un archivo CSV con una columna 'Nombre'", type=["csv"], key="uploaded_girls_file")
    if uploaded_girls_file is not None:
        try:
            df_girls = pd.read_csv(uploaded_girls_file)
            if 'Nombre' in df_girls.columns:
                all_girls = df_girls['Nombre'].dropna().astype(str).tolist()
            else:
                st.error("El archivo CSV de niñas debe contener una columna llamada 'Nombre'.")
        except Exception as e:
            st.error(f"Error al leer el archivo CSV de niñas: {e}")

if all_girls:
    st.success(f"Niñas cargadas: {len(all_girls)}")
    st.write(all_girls)
else:
    st.warning("Por favor, ingresa la lista de niñas para continuar.")

# --- Calendario de Anfitrionas ---
st.header("2. Calendario de Anfitrionas Mensuales")

hosts_input_method = st.radio(
    "¿Cómo quieres ingresar el calendario de anfitrionas?",
    ("Escribir manualmente mes a mes", "Subir archivo CSV"),
    key="hosts_input_method"
)

monthly_hosts_schedule = []
if hosts_input_method == "Escribir manualmente mes a mes":
    num_months = st.number_input("¿Cuántos meses quieres organizar?", min_value=1, value=10, key="num_months")
    for i in range(num_months):
        hosts_month_text = st.text_input(f"Anfitrionas para el Mes {i+1} (separadas por comas):", key=f"hosts_month_{i}")
        if hosts_month_text:
            hosts_this_month = [h.strip() for h in hosts_month_text.split(',') if h.strip()]
            monthly_hosts_schedule.append(hosts_this_month)

elif hosts_input_method == "Subir archivo CSV":
    uploaded_hosts_file = st.file_uploader("Sube un archivo CSV con columnas 'Mes' y 'Anfitriona'", type=["csv"], key="uploaded_hosts_file")
    if uploaded_hosts_file is not None:
        try:
            df_hosts = pd.read_csv(uploaded_hosts_file)
            if 'Mes' in df_hosts.columns and 'Anfitriona' in df_hosts.columns:
                grouped = df_hosts.groupby('Mes')['Anfitriona'].apply(list).reset_index()
                grouped = grouped.sort_values('Mes')
                for _, row in grouped.iterrows():
                    hosts_this_month = [str(h).strip() for h in row['Anfitriona'] if str(h).strip()]
                    monthly_hosts_schedule.append(hosts_this_month)
            else:
                st.error("El archivo CSV de anfitrionas debe contener columnas 'Mes' y 'Anfitriona'.")
        except Exception as e:
            st.error(f"Error al leer el archivo CSV de anfitrionas: {e}")

if monthly_hosts_schedule:
    st.success(f"Calendario de anfitrionas cargado para {len(monthly_hosts_schedule)} meses.")
    # Basic validation for hosts against all_girls
    all_hosts_flat = [host for sublist in monthly_hosts_schedule for host in sublist]
    invalid_hosts = [host for host in all_hosts_flat if host not in all_girls]
    if invalid_hosts:
        st.error(f"Advertencia: Las siguientes anfitrionas no están en la lista general de niñas: {', '.join(invalid_hosts)}. Por favor, corrige los nombres.")
    else:
        st.write("Anfitrionas por mes:", monthly_hosts_schedule)
else:
    st.warning("Por favor, ingresa el calendario de anfitrionas para continuar.")

# --- Botón de Organización ---
st.header("3. Organizar Happy Friday")

if st.button("Organizar Happy Friday", type="primary"):
    if not all_girls:
        st.error("La lista de niñas no puede estar vacía.")
    elif not monthly_hosts_schedule:
        st.error("El calendario de anfitrionas no puede estar vacío.")
    else:
        # Basic validation for hosts against all_girls again before running the organizer
        all_hosts_flat = [host for sublist in monthly_hosts_schedule for host in sublist]
        invalid_hosts = [host for host in all_hosts_flat if host not in all_girls]
        if invalid_hosts:
            st.error(f"Error: Las siguientes anfitrionas no están en la lista general de niñas: {', '.join(invalid_hosts)}. Por favor, corrige los nombres antes de organizar.")
        else:
            with st.spinner("Organizando los grupos... Esto puede tardar un momento."):
                organizer = HappyFridayOrganizer(all_girls, monthly_hosts_schedule)
                if organizer.organize_year():
                    st.success("¡Organización completada con éxito!")
                    
                    # Generate PDF in memory
                    pdf_buffer = io.BytesIO()
                    organizer.generate_pdf_report(output_filename=pdf_buffer)
                    pdf_buffer.seek(0)

                    st.download_button(
                        label="Descargar Reporte PDF",
                        data=pdf_buffer,
                        file_name="happy_friday_report.pdf",
                        mime="application/pdf"
                    )

                    st.subheader("Resumen de Asignaciones Mensuales")
                    for month_idx, assignment in enumerate(organizer.monthly_assignments):
                        st.write(f"**Mes {month_idx + 1}**")
                        df_month = pd.DataFrame([
                            {"Casa": host, "Niñas Invitadas": ", ".join([g for g in group if g != host])}
                            for host, group in assignment.items()
                        ])
                        st.dataframe(df_month, hide_index=True)
                    
                    st.subheader("Ranking de Repeticiones entre Pares de Niñas")
                    if organizer.annual_pair_counts:
                        sorted_pairs = sorted(organizer.annual_pair_counts.items(), key=lambda item: item[1], reverse=True)
                        df_ranking = pd.DataFrame([
                            {"Par de Niñas": f"{pair[0]} y {pair[1]}", "Veces Juntas": count}
                            for pair, count in sorted_pairs
                        ])
                        st.dataframe(df_ranking, hide_index=True)
                    else:
                        st.info("No se registraron repeticiones entre pares de niñas.")

                else:
                    st.error("La organización no pudo completarse. Revisa los errores en la consola o ajusta tus entradas.")

