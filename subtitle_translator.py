import sys
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QFileDialog, QTextEdit, QLabel
from googletrans import Translator
import re
import subprocess

class SubtitleTranslator(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        # Create a button to select video file
        self.selectFileBtn = QtWidgets.QPushButton('Select Video File', self)
        self.selectFileBtn.clicked.connect(self.selectFile)

        # Create a drop-down menu to select subtitle track
        self.subtitleTrackComboBox = QtWidgets.QComboBox(self)
        self.subtitleTrackComboBox.addItem('Select Subtitle Track')

        # Create a drop-down menu to select target language
        self.targetLanguageComboBox = QtWidgets.QComboBox(self)
        self.targetLanguageComboBox.addItem('Select Target Language')
        self.targetLanguageComboBox.addItem('English')
        self.targetLanguageComboBox.addItem('French')
        self.targetLanguageComboBox.addItem('Spanish')
        self.targetLanguageComboBox.addItem('Hindi')
        self.targetLanguageComboBox.addItem('Telugu')
        self.targetLanguageComboBox.addItem('Tamil')

        # Create a button to start the translation process
        self.translateBtn = QtWidgets.QPushButton('Translate Subtitles', self)
        self.translateBtn.clicked.connect(self.translateSubtitles)

        # Create a button to add the translated subtitles to the video file
        self.addSubtitlesBtn = QtWidgets.QPushButton('Add Translated Subtitles to Video', self)
        self.addSubtitlesBtn.clicked.connect(self.addSubtitlesToVideo)

        # Create a text area to display output messages
        self.outputTextEdit = QTextEdit(self)
        self.outputTextEdit.setReadOnly(True)

        # Create a label to display the selected video name
        self.videoNameLabel = QLabel(self)
        self.videoNameLabel.setText('Selected Video: None')

        # Set layout
        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.selectFileBtn)
        vbox.addWidget(self.videoNameLabel)  # Add the video name label
        vbox.addWidget(self.subtitleTrackComboBox)
        vbox.addWidget(self.targetLanguageComboBox)
        vbox.addWidget(self.translateBtn)
        vbox.addWidget(self.addSubtitlesBtn)
        vbox.addWidget(self.outputTextEdit)
        self.setLayout(vbox)

        self.fileName = ""
        self.subtitles = []
        self.subtitle_language = ""  # Store the selected target language

    def selectFile(self):
        # Open file dialog to select video file
        fileName, _ = QFileDialog.getOpenFileName(self, 'Select Video File')

        if fileName:
            self.fileName = fileName  # Store the selected file name

            # Update the video name label
            self.videoNameLabel.setText(f'Selected Video: {self.fileName}')

            # Use FFprobe to get the subtitle tracks in the video file
            probe_result = subprocess.run([
                'ffprobe',
                '-v', 'error',
                '-select_streams', 's',
                '-show_entries', 'stream_tags=language,title',
                '-of', 'csv=p=0',
                fileName
            ], capture_output=True, text=True)

            subtitle_tracks = probe_result.stdout.strip().split('\n')

            # Add the subtitle tracks to the drop-down menu
            for i, track in enumerate(subtitle_tracks):
                track_info = track.split(',')
                language_code = track_info[0]
                title = track_info[1] if len(track_info) > 1 else ""

                display_text = title if title else f'Subtitle Track {i} ({language_code})'
                self.subtitleTrackComboBox.addItem(display_text)

            self.outputTextEdit.append('Subtitle tracks loaded.')

    def extractSubtitles(self):
        # Get selected subtitle track from drop-down menu
        selected_track = self.subtitleTrackComboBox.currentText()

        if selected_track != 'Select Subtitle Track':
            track_index = self.subtitleTrackComboBox.currentIndex() - 1

            # Use FFmpeg to extract selected subtitle track and save as an SRT file
            output_subtitle = f'selected_subtitle.srt'

            subprocess.run([
                'ffmpeg',
                '-y',
                '-i', self.fileName,
                '-map', f'0:s:{track_index}',
                output_subtitle
            ])

            # Read the extracted subtitles and store lines
            with open(output_subtitle, 'r', encoding='utf-8') as f:
                self.subtitles = f.readlines()

            self.outputTextEdit.append(f'Subtitle segments extracted from {selected_track}.')

    def clean_subtitle_text(self, text):
        # Remove <i> and </i> tags
        cleaned_text = re.sub(r'<.*?>', '', text)
        return cleaned_text

    def translateSubtitles(self):
        # Extract subtitles from selected track
        self.extractSubtitles()

        # Get target language from drop-down menu
        targetLanguage = self.targetLanguageComboBox.currentText()

        if targetLanguage != 'Select Target Language':
            # Translate text lines using googletrans
            translator = Translator()
            translated_subtitles = []

            for i, line in enumerate(self.subtitles):
                if i % 4 == 2:  # Translate the third line of each segment
                    cleaned_text = self.clean_subtitle_text(line.strip())
                    translated = translator.translate(cleaned_text, src='auto', dest=targetLanguage)
                    translated_text = translated.text

                    # Clean and encode the translated text
                    cleaned_translated_text = self.clean_subtitle_text(translated_text)
                    encoded_translated_text = cleaned_translated_text.encode('utf-8')

                    # Append the cleaned and encoded text to the list
                    translated_subtitles.append(encoded_translated_text + b'\n')
                else:
                    translated_subtitles.append(line.encode('utf-8'))

            # Write the translated subtitles back to the original subtitle file
            with open('translated_subtitles.srt', 'wb') as f:
                f.writelines(translated_subtitles)

            self.outputTextEdit.append(f'Translated subtitles to {targetLanguage} and saved as translated_subtitles.srt')

            self.subtitle_language = targetLanguage

    def addSubtitlesToVideo(self):
        # Get the file extension of the original video file
        file_extension = self.fileName.split('.')[-1]

        # Use FFmpeg to add the translated SRT subtitles to the original video file
        output_video = f'output.{file_extension}'

        subprocess.run([
            'ffmpeg',
            '-i', self.fileName,
            '-i', 'translated_subtitles.srt',
            '-c', 'copy',   # Copy all streams
            '-scodec', 'srt',  # Set subtitle codec to mov_text (srt)
            '-metadata:s:s:1', f'title={self.subtitle_language}',  # Set title metadata for the new subtitle track
            '-disposition:s:1', 'default',  # Make the new subtitle stream default
            '-map', '0',    # Map all streams from input 0
            '-map', '1',    # Map subtitle stream from input 1 (the translated subtitles)
            '-y', output_video
        ])

        self.outputTextEdit.append(f'Added translated subtitles to video and saved as {output_video}')


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    ex = SubtitleTranslator()
    ex.show()
    sys.exit(app.exec_())
