from fpdf import FPDF
import os

OUTPUT = os.path.join(os.path.dirname(__file__), "Guia de Instalacion SmartEnvios.pdf")

W = 210
H = 297
LM = 15
RM = 15
PW = W - LM - RM

class PDF(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Arial", "B", 7)
        self.set_text_color(120)
        self.cell(PW, 4, "SmartEnvios - Guia de Instalacion", align="L")
        self.cell(0, 4, f"Pagina {self.page_no()}", align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(22, 163, 74)
        self.line(LM, self.get_y(), W - RM, self.get_y())
        self.ln(4)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-12)
        self.set_font("Arial", "I", 6)
        self.set_text_color(160)
        self.cell(0, 8, "By CriptoPana", align="C")

    def titulo(self, text):
        self.set_font("Arial", "B", 16)
        self.set_text_color(22, 163, 74)
        self.cell(0, 10, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def subtitulo(self, text):
        self.set_font("Arial", "B", 12)
        self.set_text_color(30, 30, 30)
        self.cell(0, 8, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def paso(self, num, tit):
        self.set_font("Arial", "B", 11)
        self.set_text_color(22, 163, 74)
        self.cell(0, 7, f"Paso {num}: {tit}", new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def cuerpo(self, text):
        self.set_font("Arial", "", 10)
        self.set_text_color(50)
        self.multi_cell(0, 5.5, text)
        self.ln(2)

    def nota(self, text):
        self.set_fill_color(255, 243, 205)
        self.set_draw_color(255, 193, 7)
        self.set_font("Arial", "I", 9)
        self.set_text_color(133, 100, 4)
        y = self.get_y()
        self.rect(LM, y, PW, 14, style="DF")
        self.set_xy(LM + 2, y + 1)
        self.multi_cell(PW - 4, 5, text)
        self.ln(4)

    def advertencia(self, text):
        self.set_fill_color(248, 215, 218)
        self.set_draw_color(220, 53, 69)
        self.set_font("Arial", "I", 9)
        self.set_text_color(114, 28, 36)
        y = self.get_y()
        self.rect(LM, y, PW, 14, style="DF")
        self.set_xy(LM + 2, y + 1)
        self.multi_cell(PW - 4, 5, text)
        self.ln(4)

    def item(self, text, bold_part=""):
        self.set_font("Arial", "", 10)
        self.set_text_color(50)
        self.cell(5, 5.5, "-")
        if bold_part:
            self.set_font("Arial", "B", 10)
            self.write(5.5, bold_part)
            self.set_font("Arial", "", 10)
            self.write(5.5, text[len(bold_part):])
        else:
            self.write(5.5, text)
        self.ln(5.5)

    def codigo(self, text):
        self.set_fill_color(40, 44, 52)
        self.set_text_color(220, 220, 220)
        self.set_font("Courier", "", 9)
        lines = text.split("\n")
        bh = len(lines) * 5.5 + 4
        y0 = self.get_y()
        self.rect(LM, y0, PW, bh, style="F")
        self.set_xy(LM + 3, y0 + 2)
        for line in lines:
            self.cell(0, 5.5, line, new_x="LMARGIN", new_y="NEXT")
            self.set_x(LM + 3)
        self.set_text_color(50)
        self.set_font("Arial", "", 10)
        self.ln(3)


def build():
    pdf = PDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)

    # ---------- PORTADA ----------
    pdf.add_page()
    pdf.ln(50)
    pdf.set_font("Arial", "B", 36)
    pdf.set_text_color(22, 163, 74)
    pdf.cell(0, 14, "SmartEnvios", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Arial", "", 16)
    pdf.set_text_color(100)
    pdf.cell(0, 10, "Guia de Instalacion", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_draw_color(22, 163, 74)
    pdf.line(70, pdf.get_y(), W - 70, pdf.get_y())
    pdf.ln(10)
    pdf.set_font("Arial", "", 11)
    pdf.set_text_color(120)
    pdf.cell(0, 7, "Plataforma de Mensajeria WhatsApp", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, "By CriptoPana", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(40)
    pdf.set_font("Arial", "I", 9)
    pdf.set_text_color(160)
    pdf.cell(0, 6, "Este documento lo genera automticamente la aplicacion.", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, "Fecha de generacion: Julio 2025", align="C", new_x="LMARGIN", new_y="NEXT")

    # ---------- INTRODUCCION ----------
    pdf.add_page()
    pdf.titulo("Introduccion")
    pdf.cuerpo(
        "SmartEnvios es una plataforma que permite enviar mensajes de WhatsApp "
        "de forma masiva desde tu PC, utilizando datos de tu base de datos DBISAM (HAC H O). "
        "Esta guia te llevara paso a paso desde un PC con Windows recien instalado "
        "hasta tener la aplicacion funcionando."
    )
    pdf.subtitulo("Requisitos minimos")
    pdf.item("Sistema operativo: Windows 10 u 11 (64 bits)")
    pdf.item("Conexion a Internet (para la instalacion inicial)")
    pdf.item("Cuenta de WhatsApp valida")
    pdf.item("Espacio en disco: 500 MB libres")
    pdf.item("Memoria RAM: 4 GB minimo")
    pdf.ln(4)
    pdf.subtitulo("Que vas a instalar")
    pdf.item("Python 3.12.9 (32 bits) - el motor que ejecuta la aplicacion")
    pdf.item("Node.js 24.14.1 - necesario para el servicio de WhatsApp")
    pdf.item("Controlador ODBC DBISAM - para conectar con tu base de datos")
    pdf.item("SmartEnvios - la aplicacion en si")

    # ---------- PASO 1: PYTHON ----------
    pdf.add_page()
    pdf.paso(1, "Instalar Python 3.12.9 (32 bits)")
    pdf.cuerpo(
        "Python es el lenguaje de programacion en el que esta escrita la mayoria "
        "de la aplicacion. Necesitamos una version especifica (32 bits)."
    )
    pdf.subtitulo("Pasos:")
    pdf.item("Abre tu navegador web (Chrome, Edge, etc.).")
    pdf.item(
        "Ve a la pagina de descargas de Python: "
        "https://www.python.org/downloads/release/python-3129/"
    )
    pdf.item(
        'Desplazate hacia abajo hasta la seccion "Files" y descarga el archivo:',
        bold_part=""
    )
    pdf.codigo("python-3.12.9.exe")
    pdf.item('Ejecuta el archivo descargado (python-3.12.9.exe).')
    pdf.item(
        "IMPORTANTE: En la primera pantalla, MARCA la casilla que dice "
        '"Add Python to PATH" (Agregar Python al PATH).',
        bold_part="IMPORTANTE: "
    )
    pdf.item('Luego haz clic en "Install Now" (Instalar ahora).')
    pdf.item("Espera a que termine la instalacion (puede tomar 1-2 minutos).")
    pdf.item('Al finalizar, haz clic en "Close" (Cerrar).')
    pdf.nota(
        "Nota: Si ya tienes Python instalado pero no sabes si es 32 bits, "
        "abre una terminal (simbolo del sistema) y escribe: python --version. "
        "Si ves 'Python 3.12.9' estas bien."
    )

    # ---------- PASO 2: NODE.JS ----------
    pdf.add_page()
    pdf.paso(2, "Instalar Node.js 24.14.1")
    pdf.cuerpo(
        "Node.js se encarga del servicio que se conecta con WhatsApp Web. "
        "Sin el, la aplicacion no podra enviar mensajes."
    )
    pdf.subtitulo("Pasos:")
    pdf.item("Abre tu navegador y ve a la pagina oficial de Node.js:")
    pdf.codigo("https://nodejs.org/")
    pdf.item(
        'Haz clic en el boton verde grande que dice "LTS" (Recommended for most users). '
        "Esto descargara la version estable mas reciente (compatible con la que necesitamos)."
    )
    pdf.item('Ejecuta el archivo descargado (Node-v24.14.1-x64.msi o similar).')
    pdf.item(
        'Deja todas las opciones por defecto y haz clic en "Next" (Siguiente) '
        'en cada pantalla, luego en "Install" (Instalar).'
    )
    pdf.item("Espera a que termine la instalacion.")
    pdf.item('Al finalizar, haz clic en "Finish" (Finalizar).')

    # ---------- PASO 3: DBISAM ODBC ----------
    pdf.add_page()
    pdf.paso(3, "Instalar controlador ODBC de DBISAM")
    pdf.cuerpo(
        "Este controlador permite que la aplicacion se conecte a tu base de datos "
        "DBISAM (HAC H O) donde tienes almacenados tus clientes y facturas."
    )
    pdf.subtitulo("Pasos:")
    pdf.item(
        "Busca el archivo 'DBISAM_ODBC.exe' en la carpeta de la aplicacion "
        "(esta incluido en la carpeta 'instaladores' o preguntale al desarrollador)."
    )
    pdf.item('Ejecuta el archivo "DBISAM_ODBC.exe" como Administrador.')
    pdf.item('Sigue las instrucciones del instalador con las opciones por defecto.')
    pdf.item("Reinicia la computadora cuando te lo pida (o al finalizar la instalacion).")

    pdf.subtitulo("Configurar el DSN (nombre de la conexion)")
    pdf.item('Presiona la tecla "Windows" y escribe "ODBC".')
    pdf.item(
        'Selecciona "Herramientas ODBC (32 bits)" - es importante elegir la de 32 bits.',
        bold_part="32 bits"
    )
    pdf.item('Ve a la pestana "DSN de Sistema" (System DSN).')
    pdf.item('Haz clic en "Agregar" (Add).')
    pdf.item(
        'De la lista, selecciona "DBISAM 4 ODBC Driver" y haz clic en "Finalizar".'
    )
    pdf.item('En "Data Source Name" (Nombre del origen de datos) escribe exactamente:')
    pdf.codigo("HAC_HO")
    pdf.item(
        'En "Database Directory" (Directorio de la base de datos) selecciona '
        "la carpeta donde tienes los archivos DBISAM de tu sistema (ej: C:\\HAC\\Datos)."
    )
    pdf.item('Haz clic en "OK" para guardar.')
    pdf.advertencia(
        "ADVERTENCIA: El nombre del DSN debe ser exactamente 'HAC_HO', "
        "con mayusculas y sin espacios. La aplicacion no funcionara si el nombre es diferente."
    )

    # ---------- PASO 4: COPIAR APP ----------
    pdf.add_page()
    pdf.paso(4, "Copiar la aplicacion SmartEnvios")
    pdf.cuerpo(
        "La aplicacion SmartEnvios viene en una carpeta que te proporciona el desarrollador. "
        "Debes copiarla a una ubicacion definitiva en tu computadora."
    )
    pdf.subtitulo("Pasos:")
    pdf.item(
        "Conecta el dispositivo USB o accede al archivo comprimido "
        "(ZIP/RAR) donde recibiste la aplicacion."
    )
    pdf.item(
        "Copia toda la carpeta 'SmartEnvios' a una ubicacion en tu disco duro. "
        "Ejemplos de buenas ubicaciones:"
    )
    pdf.item("C:\\SmartEnvios")
    pdf.item("D:\\SmartEnvios")
    pdf.item("C:\\Users\\TuUsuario\\SmartEnvios")
    pdf.item(
        "IMPORTANTE: No uses carpetas con espacios o caracteres especiales "
        "en la ruta. La ruta no debe contener acentos, enes (~) ni espacios largos.",
        bold_part="IMPORTANTE: "
    )
    pdf.item(
        'Si la carpeta viene comprimida (ZIP), haz clic derecho sobre ella '
        'y selecciona "Extraer aqui" o "Extract all".'
    )
    pdf.nota(
        "Nota: La carpeta de la aplicacion contiene todo lo necesario: "
        "el launcher, el backend (Python), el frontend (interface web) "
        "y el servicio de WhatsApp."
    )

    # ---------- PASO 5: DEPENDENCIAS PYTHON ----------
    pdf.add_page()
    pdf.paso(5, "Instalar dependencias de Python")
    pdf.cuerpo(
        "La aplicacion necesita varias librerias de Python adicionales para funcionar. "
        "Las instalaremos todas automaticamente con un solo comando."
    )
    pdf.subtitulo("Pasos:")
    pdf.item('Abre la carpeta donde copiaste la aplicacion.')
    pdf.item(
        'Haz clic en la barra de direcciones del Explorador de Archivos, '
        'escribe "cmd" y presiona Enter. Se abrira una ventana negra (terminal).'
    )
    pdf.item("En la ventana negra, escribe el siguiente comando y presiona Enter:")
    pdf.codigo('python -m pip install --upgrade pip')
    pdf.item("Espera a que termine (puede tomar 30 segundos).")
    pdf.item("Luego escribe este comando y presiona Enter:")
    pdf.codigo('python -m pip install -r backend\\requirements.txt')
    pdf.item(
        "Este proceso descargara e instalara todas las librerias necesarias. "
        "Puede tomar varios minutos (3-10 minutos dependiendo de tu internet)."
    )
    pdf.item("Cuando termine, veras un mensaje verde que dice 'Successfully installed...'")
    pdf.advertencia(
        "ADVERTENCIA: Si ves errores en rojo, asegurate de que Python 3.12.9 "
        "(32 bits) esta correctamente instalado y que marcaste la casilla "
        "'Add Python to PATH' en el Paso 1. Si el error persiste, contacta al desarrollador."
    )

    # ---------- PASO 6: NPM + BUILD ----------
    pdf.add_page()
    pdf.paso(6, "Instalar dependencias de Node.js y compilar")
    pdf.cuerpo(
        "La interfaz web que ves en el navegador tambien necesita prepararse. "
        "Esto se hace con dos comandos."
    )
    pdf.subtitulo("Pasos:")
    pdf.item(
        "Asegurate de tener la terminal abierta en la carpeta de la aplicacion "
        "(si la cerraste, vuelve a abrirla como en el Paso 5)."
    )
    pdf.item("Escribe el siguiente comando y presiona Enter:")
    pdf.codigo('cd frontend')
    pdf.item("Luego escribe:")
    pdf.codigo('npm install')
    pdf.item(
        "Esto descargara todas las librerias de la interfaz web. "
        "Puede tomar 2-5 minutos."
    )
    pdf.item("Cuando termine, escribe:")
    pdf.codigo('npm run build')
    pdf.item("Esto compila la interfaz web. Debe tomar menos de 1 minuto.")
    pdf.item("Cuando termine, veras un mensaje como 'build complete'.")
    pdf.item('Finalmente, escribe "cd .." para volver a la carpeta principal:')
    pdf.codigo('cd ..')
    pdf.nota(
        "Nota: El comando 'npm run build' solo es necesario la primera vez "
        "o cuando el desarrollador actualice la aplicacion. En uso normal no se repite."
    )

    # ---------- PASO 7: LICENCIA ----------
    pdf.add_page()
    pdf.paso(7, "Obtener y colocar la licencia")
    pdf.cuerpo(
        "SmartEnvios requiere una licencia para funcionar. La licencia esta vinculada "
        "al hardware de tu computadora, por lo que debes generar una unica para cada PC."
    )
    pdf.subtitulo("Pasos:")
    pdf.item("Ejecuta el archivo 'ejecutar.bat' o 'launcher.pyw' dentro de la carpeta.")
    pdf.item(
        "La aplicacion se iniciara pero mostrara una pantalla con un "
        '"Codigo de Maquina" (un texto largo) y un mensaje de "Sin licencia valida".'
    )
    pdf.item(
        "Selecciona el codigo de maquina con el mouse, haz clic derecho y elige 'Copiar'."
    )
    pdf.item("Envia ese codigo al desarrollador para que genere tu licencia.")
    pdf.item(
        "El desarrollador te devolvera un archivo llamado 'license.lic'. "
        "Coloca ese archivo en la carpeta principal de la aplicacion "
        "(donde esta 'ejecutar.bat')."
    )
    pdf.item("Vuelve a ejecutar 'ejecutar.bat'. Ahora la aplicacion deberia iniciar normalmente.")
    pdf.advertencia(
        "ADVERTENCIA: No cambies ni formatees el disco duro ni la placa madre "
        "de la computadora donde instalaste la licencia, porque la licencia "
        "dejara de funcionar y tendras que solicitar una nueva."
    )

    # ---------- PASO 8: EJECUTAR ----------
    pdf.add_page()
    pdf.paso(8, "Ejecutar SmartEnvios")
    pdf.cuerpo(
        "Una vez que todo esta instalado, iniciar la aplicacion es muy simple."
    )
    pdf.subtitulo("Pasos:")
    pdf.item("Ve a la carpeta de SmartEnvios en tu explorador de archivos.")
    pdf.item('Haz doble clic en el archivo "ejecutar.bat" (o "launcher.pyw").')
    pdf.item(
        "Se abrira una ventana con un progreso. La aplicacion iniciara automaticamente:"
    )
    pdf.item("1. El servicio backend (motor principal)")
    pdf.item("2. El servicio de WhatsApp (conexion con tu cuenta)")
    pdf.item("3. La interfaz web en tu navegador")
    pdf.item(
        "La primera vez, se abrira WhatsApp Web en una ventana aparte. "
        "Escanea el codigo QR con tu telefono para vincular tu cuenta de WhatsApp."
    )
    pdf.item(
        "Una vez vinculada, la aplicacion cargara automaticamente "
        "la interfaz principal en el navegador."
    )
    pdf.item(
        "Si cierras la ventana del navegador, puedes volver a abrirla "
        "yendo a: http://localhost:5173"
    )
    pdf.nota(
        "Nota: La aplicacion se minimiza a la bandeja del sistema "
        "(junto al reloj de Windows). Puedes hacer clic derecho en su icono "
        "para abrir la ventana o cerrar la aplicacion por completo."
    )

    # ---------- SOLUCION DE PROBLEMAS ----------
    pdf.add_page()
    pdf.titulo("Solucion de problemas")
    pdf.subtitulo("La aplicacion no inicia")
    pdf.item("Verifica que Python 3.12.9 esta instalado: abre una terminal y escribe:")
    pdf.codigo("python --version")
    pdf.item("Deberias ver: Python 3.12.9")
    pdf.item("Verifica que Node.js esta instalado:")
    pdf.codigo("node --version")
    pdf.item("Deberias ver: v24.14.1 (o similar)")

    pdf.subtitulo("Error de conexion a la base de datos")
    pdf.item("Verifica que el DSN 'HAC_HO' existe en Herramientas ODBC (32 bits).")
    pdf.item("Verifica que la carpeta de datos DBISAM sea la correcta.")
    pdf.item("Verifica que los archivos DBISAM no esten siendo usados por otro programa.")

    pdf.subtitulo("WhatsApp no se conecta")
    pdf.item("Asegurate de tener internet.")
    pdf.item("La primera vez, escanea el codigo QR con tu telefono.")
    pdf.item("Si falla, desde la interfaz web ve a 'WhatsApp' y haz clic en 'Cerrar Sesion'.")
    pdf.item("Luego vuelve a iniciar sesion escaneando el nuevo codigo QR.")

    pdf.subtitulo("Error 'No hay licencia valida'")
    pdf.item("Verifica que el archivo 'license.lic' esta en la carpeta principal.")
    pdf.item("Verifica que el nombre del archivo sea exactamente 'license.lic' (sin mayusculas).")
    pdf.item("Si lo perdiste, contacta al desarrollador para obtener uno nuevo.")

    # ---------- CONTACTO ----------
    pdf.add_page()
    pdf.titulo("Contacto y soporte")
    pdf.cuerpo(
        "Si tienes problemas con la instalacion o el funcionamiento de SmartEnvios, "
        "contacta al desarrollador."
    )
    pdf.item("Desarrollador: CriptoPana")
    pdf.item("Aplicacion: SmartEnvios")
    pdf.item("By CriptoPana")
    pdf.ln(10)
    pdf.set_font("Arial", "I", 9)
    pdf.set_text_color(160)
    pdf.multi_cell(0, 5, "Documento generado automaticamente por la aplicacion SmartEnvios.")

    pdf.output(OUTPUT)
    print(f"PDF generado: {OUTPUT}")


if __name__ == "__main__":
    build()
