from flask import Flask, request, render_template
from werkzeug.utils import secure_filename
import pytesseract
from PIL import Image, ImageDraw, ImageFont
from mtranslate import translate
import os
import io
import base64
from langdetect import detect, LangDetectException


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.abspath('uploads')
app.config['UNTRANSLATED_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'без перевода')
app.config['TRANSLATED_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'с переводом')
app.secret_key = "136843156521"
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def make_image(text, filename):
    img = Image.new('RGB', (800, 1000), color='white')
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except IOError:
        font = ImageFont.load_default()
    d.text((10, 10), text, fill=(0, 0, 0), font=font)
    img_byte = io.BytesIO()
    img.save(img_byte, format='PNG')
    img_byte = img_byte.getvalue()
    return base64.b64encode(img_byte).decode()


@app.route('/', methods=['GET', 'POST'])
def upload_translate():
    if request.method == 'POST':
        if 'file' not in request.files or request.files['file'].filename == '':
            return 'Ошибка: файл не выбран.'

        file = request.files['file']
        filename = secure_filename(file.filename)
        filepath_untranslated = os.path.join(app.config['UNTRANSLATED_FOLDER'], filename)

        try:
            file.save(filepath_untranslated)
            img = Image.open(filepath_untranslated)

            if img.format not in ('JPEG', 'PNG', 'TIFF'):
                img.close()
                os.remove(filepath_untranslated)
                return 'Ошибка: Неподдерживаемый формат файла.'

            extracted = pytesseract.image_to_string(img, lang='chi_sim')
            if not extracted.strip():
                extracted = pytesseract.image_to_string(img, lang='eng')
            if not extracted.strip():
                os.remove(filepath_untranslated)
                return "Ошибка: Текст не распознан."

            try:
                detected = detect(extracted)
                supported = ['ru', 'en', 'de', 'fr', 'es', 'it']
                if detected not in supported:
                    os.remove(filepath_untranslated)
                    return ("Ошибка: Текст на изображении не на одном из поддерживаемых языков "
                            "(русский, английский, немецкий, французский, испанский, итальянский).")

                target = request.form.get('target_language', 'ru')
                translated = translate(extracted, target)
                if detected == target:
                    os.remove(filepath_untranslated)
                    return "Ошибка: Изображение уже написано на данном языке. Перевод не нужен."

                original_img = make_image(extracted, "original.png")
                translated_img = make_image(translated, "translated.png")

                translated_img_to_path = os.path.join(app.config['TRANSLATED_FOLDER'], "translated_" + filename)
                with open(translated_img_to_path, "wb") as f:
                    f.write(base64.b64decode(translated_img))

                return render_template('result.html',
                                       original_text=extracted,
                                       translated_text=translated,
                                       target_language=target,
                                       original_image=original_img,
                                       translated_image=translated_img)
            except LangDetectException:
                img.close()
                os.remove(filepath_untranslated)
                return "Ошибка: Не удалось определить язык текста на изображении."

        except FileNotFoundError:
            return "Ошибка: Файл не найден."
        except (IOError, OSError) as e:
            return f"Ошибка ввода-вывода: {e}"
        except Exception as e:
            return f"Произошла неизвестная ошибка: {type(e).__name__}: {e}"

    return render_template('index.html')


if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['UNTRANSLATED_FOLDER'], exist_ok=True)
    os.makedirs(app.config['TRANSLATED_FOLDER'], exist_ok=True)
    app.run(debug=True)
