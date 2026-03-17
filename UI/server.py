#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔═══════════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                           ║
║     ██████╗ ██████╗  ██████╗ ███████╗███████╗████████╗ █████╗     ██╗   ██╗██╗            ║
║     ██╔══██╗██╔══██╗██╔═══██╗██╔════╝██╔════╝╚══██╔══╝██╔══██╗    ██║   ██║██║            ║
║     ██████╔╝██████╔╝██║   ██║█████╗  █████╗     ██║   ███████║    ██║   ██║██║            ║
║     ██╔═══╝ ██╔══██╗██║   ██║██╔══╝  ██╔══╝     ██║   ██╔══██║    ██║   ██║██║            ║
║     ██║     ██║  ██║╚██████╔╝██║     ███████╗   ██║   ██║  ██║    ╚██████╔╝██║            ║
║     ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚══════╝   ╚═╝   ╚═╝  ╚═╝     ╚═════╝ ╚═╝            ║
║                                                                                           ║
║                    PROFETA Universal v5.0 - Enterprise Dashboard                          ║
║                              Web Monitoring Interface                                     ║
║                                                                                           ║
╠═══════════════════════════════════════════════════════════════════════════════════════════╣
║  Autore      : Ing. Emilio Billi                                                          ║
║  Azienda     : BilliDynamics™                                                             ║
║  Versione    : 1.0.0                                                                      ║
║  Licenza     : Proprietaria - Tutti i diritti riservati                                   ║
╚═══════════════════════════════════════════════════════════════════════════════════════════╝

Dashboard di monitoraggio autocontenuta per PROFETA Universal v5.0.
Architettura non-invasiva: solo lettura dei file di output, nessuna modifica al core.

Requisiti:
    pip install flask flask-cors

Utilizzo:
    python server.py [--config PATH] [--port PORT] [--host HOST]
    
    Opzioni:
        --config    Path al file config-lstm.ini (default: ../config-lstm.ini)
        --port      Porta HTTP (default: 5000)  
        --host      Host binding (default: 127.0.0.1)
        --debug     Abilita modalità debug

Esempio:
    python server.py --config /path/to/profeta/config-lstm.ini --port 8080
"""

import os
import sys
import json
import re
import csv
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from configparser import ConfigParser, RawConfigParser
import logging

# ═══════════════════════════════════════════════════════════════════════════════
# FLASK IMPORTS
# ═══════════════════════════════════════════════════════════════════════════════

try:
    from flask import Flask, render_template, jsonify, request, send_from_directory
    from flask_cors import CORS
except ImportError:
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║  ERRORE: Dipendenze mancanti                                      ║")
    print("╠═══════════════════════════════════════════════════════════════════╣")
    print("║  Installa le dipendenze con:                                      ║")
    print("║                                                                   ║")
    print("║    pip install flask flask-cors                                   ║")
    print("║                                                                   ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAZIONE LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s │ %(levelname)-8s │ %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('PROFETA-UI')

# ═══════════════════════════════════════════════════════════════════════════════
# COSTANTI
# ═══════════════════════════════════════════════════════════════════════════════

VERSION = "1.0.0"
APP_NAME = "PROFETA Universal Dashboard"

# Pattern per parsing valori Python embedded nel CSV (es: np.float64(...))
NUMPY_PATTERN = re.compile(r"np\.float64\(([\d\.\-e]+)\)")

# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ConfigSection:
    """Rappresenta una sezione del file INI"""
    name: str
    parameters: Dict[str, Any]
    comments: Dict[str, str]  # Commenti per ogni parametro
    
@dataclass
class SystemStatus:
    """Stato corrente del sistema"""
    config_loaded: bool
    config_path: str
    config_mtime: Optional[str]
    predictions_csv_path: Optional[str]
    predictions_csv_mtime: Optional[str]
    predictions_csv_rows: int
    predictions_json_path: Optional[str]
    predictions_json_mtime: Optional[str]
    predictions_json_count: int
    last_prediction_time: Optional[str]
    uptime: str
    version: str

# ═══════════════════════════════════════════════════════════════════════════════
# PARSER INI AVANZATO
# ═══════════════════════════════════════════════════════════════════════════════

class AdvancedINIParser:
    """
    Parser INI avanzato che estrae anche i commenti per ogni parametro.
    Gestisce il formato ricco di documentazione del config PROFETA.
    """
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.sections: Dict[str, ConfigSection] = {}
        self._parse()
    
    def _parse(self):
        """Parsing completo del file INI con estrazione commenti"""
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"File INI non trovato: {self.filepath}")
        
        with open(self.filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        current_section = None
        current_comments = []
        
        for line in lines:
            stripped = line.strip()
            
            # Sezione
            if stripped.startswith('[') and stripped.endswith(']'):
                section_name = stripped[1:-1]
                current_section = section_name
                self.sections[section_name] = ConfigSection(
                    name=section_name,
                    parameters={},
                    comments={}
                )
                current_comments = []
                continue
            
            # Commento
            if stripped.startswith(';') or stripped.startswith('#'):
                # Pulisci il commento
                comment = stripped.lstrip(';#').strip()
                # Ignora linee decorative (box ASCII)
                if not self._is_decorative(comment):
                    current_comments.append(comment)
                continue
            
            # Parametro
            if '=' in stripped and current_section:
                key, value = stripped.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Rimuovi commenti inline
                if ';' in value:
                    value = value.split(';')[0].strip()
                
                # Converti tipi
                parsed_value = self._parse_value(value)
                
                self.sections[current_section].parameters[key] = parsed_value
                
                # Associa commenti precedenti
                if current_comments:
                    # Prendi solo le ultime righe rilevanti del commento
                    relevant_comments = self._extract_relevant_comments(current_comments)
                    self.sections[current_section].comments[key] = relevant_comments
                    current_comments = []
    
    def _is_decorative(self, line: str) -> bool:
        """Verifica se una linea è puramente decorativa"""
        decorative_chars = set('═─│┌┐└┘├┤┬┴┼╔╗╚╝╠╣╦╩╬║━┃▀▄█▌▐░▒▓')
        if not line:
            return True
        # Se più del 70% sono caratteri decorativi, è una linea decorativa
        deco_count = sum(1 for c in line if c in decorative_chars or c == ' ')
        return deco_count / len(line) > 0.7 if line else True
    
    def _extract_relevant_comments(self, comments: List[str]) -> str:
        """Estrae i commenti rilevanti per un parametro"""
        # Filtra commenti vuoti e prendi gli ultimi 3
        relevant = [c for c in comments if c and len(c) > 5][-3:]
        return ' '.join(relevant)
    
    def _parse_value(self, value: str) -> Any:
        """Converte una stringa in tipo appropriato"""
        # Boolean
        if value.lower() in ('true', 'yes', 'on', '1'):
            return True
        if value.lower() in ('false', 'no', 'off', '0'):
            return False
        
        # None
        if value.lower() in ('none', 'null', ''):
            return None
        
        # Numeri
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass
        
        # Lista (comma-separated)
        if ',' in value:
            return [v.strip() for v in value.split(',')]
        
        return value
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte in dizionario serializzabile"""
        return {
            name: {
                'parameters': section.parameters,
                'comments': section.comments
            }
            for name, section in self.sections.items()
        }
    
    def get_section(self, name: str) -> Optional[ConfigSection]:
        """Ottiene una sezione specifica"""
        return self.sections.get(name)

# ═══════════════════════════════════════════════════════════════════════════════
# PARSER CSV PREVISIONI
# ═══════════════════════════════════════════════════════════════════════════════

class PredictionsCSVParser:
    """Parser per il CSV delle previsioni con gestione dei tipi numpy embedded"""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.data: List[Dict[str, Any]] = []
        self._parse()
    
    def _parse(self):
        """Parsing del CSV con conversione tipi"""
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"CSV non trovato: {self.filepath}")
        
        with open(self.filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                parsed_row = {}
                for key, value in row.items():
                    parsed_row[key] = self._parse_value(key, value)
                self.data.append(parsed_row)
    
    def _parse_value(self, key: str, value: str) -> Any:
        """Converte valori con gestione speciale per numpy e dict embedded"""
        if not value:
            return None
        
        # Gestisci class_probs (dizionario Python embedded)
        if key == 'class_probs':
            return self._parse_class_probs(value)
        
        # Boolean
        if value.lower() == 'true':
            return True
        if value.lower() == 'false':
            return False
        
        # Numeri
        try:
            if 'e' in value.lower() or '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass
        
        return value
    
    def _parse_class_probs(self, value: str) -> Dict[str, float]:
        """Parsing speciale per class_probs con np.float64"""
        result = {}
        
        # Estrai tutti i valori np.float64
        # Pattern: 'KEY': np.float64(VALUE)
        pattern = r"'(\w+)':\s*np\.float64\(([\d\.\-e]+)\)"
        matches = re.findall(pattern, value)
        
        for key, val in matches:
            result[key] = float(val)
        
        return result if result else {'DOWN': 0.33, 'FLAT': 0.34, 'UP': 0.33}
    
    def to_list(self) -> List[Dict[str, Any]]:
        """Restituisce i dati come lista"""
        return self.data
    
    def get_statistics(self) -> Dict[str, Any]:
        """Calcola statistiche aggregate"""
        if not self.data:
            return {}
        
        signals = {}
        classes = {}
        confidences = []
        
        for row in self.data:
            # Conta segnali
            signal = row.get('signal', 'UNKNOWN')
            signals[signal] = signals.get(signal, 0) + 1
            
            # Conta classi
            cls = row.get('class', 'UNKNOWN')
            classes[cls] = classes.get(cls, 0) + 1
            
            # Raccogli confidence
            conf = row.get('confidence', 0)
            if isinstance(conf, (int, float)):
                confidences.append(conf)
        
        return {
            'total_predictions': len(self.data),
            'signals_distribution': signals,
            'classes_distribution': classes,
            'avg_confidence': sum(confidences) / len(confidences) if confidences else 0,
            'min_confidence': min(confidences) if confidences else 0,
            'max_confidence': max(confidences) if confidences else 0,
            'first_timestamp': self.data[0].get('timestamp') if self.data else None,
            'last_timestamp': self.data[-1].get('timestamp') if self.data else None
        }

# ═══════════════════════════════════════════════════════════════════════════════
# PARSER JSON PREVISIONI
# ═══════════════════════════════════════════════════════════════════════════════

class PredictionsJSONParser:
    """Parser per il JSON delle previsioni con metriche"""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.data: Dict[str, Any] = {}
        self._parse()
    
    def _parse(self):
        """Carica e valida il JSON"""
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"JSON non trovato: {self.filepath}")
        
        with open(self.filepath, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
    
    def get_metadata(self) -> Dict[str, Any]:
        """Restituisce i metadati"""
        return self.data.get('metadata', {})
    
    def get_metrics(self) -> Dict[str, Any]:
        """Restituisce le metriche"""
        return self.data.get('metrics', {})
    
    def get_predictions(self, limit: int = None, offset: int = 0) -> List[Dict[str, Any]]:
        """Restituisce le previsioni con paginazione opzionale"""
        predictions = self.data.get('predictions', [])
        if limit:
            return predictions[offset:offset + limit]
        return predictions
    
    def get_predictions_count(self) -> int:
        """Numero totale di previsioni"""
        return len(self.data.get('predictions', []))
    
    def get_signals_summary(self) -> Dict[str, int]:
        """Sommario dei segnali"""
        signals = {}
        for pred in self.data.get('predictions', []):
            signal = pred.get('signal', 'UNKNOWN')
            signals[signal] = signals.get(signal, 0) + 1
        return signals

# ═══════════════════════════════════════════════════════════════════════════════
# APPLICATION FACTORY
# ═══════════════════════════════════════════════════════════════════════════════

def get_paths_from_config(config_path: str) -> Dict[str, Optional[str]]:
    """
    Estrae i percorsi dei file di output dal file di configurazione INI.
    
    Args:
        config_path: Path al file config-lstm.ini
    
    Returns:
        Dict con:
            - csv_path: Percorso del file CSV previsioni (da [PREDICTION] output_predictions_path)
            - json_dir: Directory output JSON (da [PREDICTION] output_dir)
    """
    paths = {
        'csv_path': None,
        'json_dir': None,
        'config_dir': None
    }
    
    if not config_path or not os.path.exists(config_path):
        return paths
    
    config_dir = Path(config_path).parent
    paths['config_dir'] = str(config_dir)
    
    try:
        parser = AdvancedINIParser(config_path)
        
        # Ottieni sezione PREDICTION
        prediction_section = parser.get_section('PREDICTION')
        if prediction_section:
            params = prediction_section.parameters
            
            # CSV delle previsioni: output_predictions_path
            csv_path = params.get('output_predictions_path')
            if csv_path:
                # Risolvi path relativo rispetto alla directory del config
                csv_path = str(csv_path)
                if not os.path.isabs(csv_path):
                    csv_path = str(config_dir / csv_path)
                paths['csv_path'] = csv_path
                logger.info(f"CSV path dal config: {csv_path}")
            
            # Directory output per JSON: output_dir
            json_dir = params.get('output_dir')
            if json_dir:
                json_dir = str(json_dir)
                if not os.path.isabs(json_dir):
                    json_dir = str(config_dir / json_dir)
                paths['json_dir'] = json_dir
                logger.info(f"JSON dir dal config: {json_dir}")
        
    except Exception as e:
        logger.warning(f"Impossibile leggere percorsi dal config: {e}")
    
    return paths


def create_app(config_path: str = None) -> Flask:
    """
    Factory per creare l'applicazione Flask.
    
    Args:
        config_path: Path al file config-lstm.ini di PROFETA
    
    Returns:
        Istanza Flask configurata
    """
    
    # Determina i path
    base_dir = Path(__file__).parent
    
    app = Flask(
        __name__,
        template_folder=str(base_dir / 'templates'),
        static_folder=str(base_dir / 'static')
    )
    
    # Abilita CORS per sviluppo
    CORS(app)
    
    # Memorizza configurazione
    app.config['CONFIG_PATH'] = config_path
    app.config['START_TIME'] = datetime.now()
    
    # Estrai percorsi dal file di configurazione
    config_paths = get_paths_from_config(config_path)
    app.config['CSV_PATH'] = config_paths.get('csv_path')
    app.config['JSON_DIR'] = config_paths.get('json_dir')
    
    # Cerca automaticamente i file nella directory padre se non specificati
    if config_path:
        config_dir = Path(config_path).parent
    else:
        config_dir = base_dir.parent
    
    app.config['CONFIG_DIR'] = str(config_dir)
    
    # ═══════════════════════════════════════════════════════════════════════
    # ROUTES - PAGINE
    # ═══════════════════════════════════════════════════════════════════════
    
    @app.route('/')
    def index():
        """Pagina principale della dashboard"""
        return render_template('index.html')
    
    # ═══════════════════════════════════════════════════════════════════════
    # ROUTES - API
    # ═══════════════════════════════════════════════════════════════════════
    
    @app.route('/api/status')
    def api_status():
        """Stato del sistema"""
        config_path = app.config.get('CONFIG_PATH')
        config_dir = Path(app.config.get('CONFIG_DIR', '.'))
        
        # Usa i percorsi dal config INI se disponibili
        csv_path = app.config.get('CSV_PATH')
        json_dir = app.config.get('JSON_DIR')
        json_path = None
        
        # Se CSV path è dal config, verificane l'esistenza
        if csv_path and not os.path.exists(csv_path):
            logger.warning(f"CSV path dal config non trovato: {csv_path}")
            csv_path = None
        
        # Cerca JSON nella directory specificata dal config o fallback
        if json_dir and os.path.exists(json_dir):
            json_files = list(Path(json_dir).glob('predictions.json'))
            if json_files:
                json_path = str(json_files[0])
        
        # Fallback: cerca con pattern se non trovato dal config
        if not csv_path:
            for subdir in ['PREVISIONI', 'output', '.', 'data']:
                pattern_dir = config_dir / subdir
                if pattern_dir.exists():
                    csv_files = list(pattern_dir.glob('real_time_*.csv'))
                    if csv_files:
                        csv_path = str(max(csv_files, key=os.path.getmtime))
                        break
                    csv_files = list(pattern_dir.glob('*predictions*.csv'))
                    if csv_files:
                        csv_path = str(max(csv_files, key=os.path.getmtime))
                        break
        
        if not json_path:
            for subdir in ['output', '.', 'data']:
                pattern_dir = config_dir / subdir
                if pattern_dir.exists():
                    json_files = list(pattern_dir.glob('predictions.json'))
                    if json_files:
                        json_path = str(json_files[0])
                        break
        
        # Costruisci status
        csv_rows = 0
        csv_mtime = None
        json_count = 0
        json_mtime = None
        last_pred = None
        
        if csv_path and os.path.exists(csv_path):
            csv_mtime = datetime.fromtimestamp(os.path.getmtime(csv_path)).isoformat()
            with open(csv_path, 'r') as f:
                csv_rows = sum(1 for _ in f) - 1  # Escludi header
            try:
                parser = PredictionsCSVParser(csv_path)
                if parser.data:
                    last_pred = parser.data[-1].get('timestamp')
            except:
                pass
        
        if json_path and os.path.exists(json_path):
            json_mtime = datetime.fromtimestamp(os.path.getmtime(json_path)).isoformat()
            try:
                parser = PredictionsJSONParser(json_path)
                json_count = parser.get_predictions_count()
            except:
                pass
        
        # Calcola uptime
        uptime_delta = datetime.now() - app.config['START_TIME']
        hours, remainder = divmod(int(uptime_delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        status = SystemStatus(
            config_loaded=config_path is not None and os.path.exists(config_path) if config_path else False,
            config_path=config_path or "Non specificato",
            config_mtime=datetime.fromtimestamp(os.path.getmtime(config_path)).isoformat() if config_path and os.path.exists(config_path) else None,
            predictions_csv_path=csv_path,
            predictions_csv_mtime=csv_mtime,
            predictions_csv_rows=csv_rows,
            predictions_json_path=json_path,
            predictions_json_mtime=json_mtime,
            predictions_json_count=json_count,
            last_prediction_time=last_pred,
            uptime=uptime_str,
            version=VERSION
        )
        
        return jsonify(asdict(status))
    
    @app.route('/api/config')
    def api_config():
        """Configurazione INI parsata"""
        config_path = app.config.get('CONFIG_PATH')
        
        if not config_path or not os.path.exists(config_path):
            return jsonify({'error': 'File di configurazione non trovato', 'sections': {}}), 404
        
        try:
            parser = AdvancedINIParser(config_path)
            return jsonify({
                'path': config_path,
                'sections': parser.to_dict()
            })
        except Exception as e:
            logger.error(f"Errore parsing config: {e}")
            return jsonify({'error': str(e), 'sections': {}}), 500
    
    @app.route('/api/predictions/csv')
    def api_predictions_csv():
        """Previsioni dal CSV (fonte primaria - percorso da config INI)"""
        config_dir = Path(app.config.get('CONFIG_DIR', '.'))
        
        # Usa il percorso dal config INI come fonte primaria
        csv_path = app.config.get('CSV_PATH')
        
        # Verifica esistenza del file dal config
        if csv_path and not os.path.exists(csv_path):
            logger.warning(f"CSV dal config non trovato: {csv_path}")
            csv_path = None
        
        # Fallback: cerca con pattern se non trovato dal config
        if not csv_path:
            for subdir in ['PREVISIONI', 'output', '.', 'data']:
                pattern_dir = config_dir / subdir
                if pattern_dir.exists():
                    csv_files = list(pattern_dir.glob('real_time_*.csv'))
                    if csv_files:
                        csv_path = str(max(csv_files, key=os.path.getmtime))
                        break
        
        if not csv_path:
            return jsonify({
                'error': 'CSV previsioni non trovato. Verificare output_predictions_path nel file INI.',
                'config_csv_path': app.config.get('CSV_PATH'),
                'data': [],
                'statistics': {}
            }), 404
        
        try:
            parser = PredictionsCSVParser(csv_path)
            
            # Paginazione
            limit = request.args.get('limit', type=int)
            offset = request.args.get('offset', 0, type=int)
            
            data = parser.to_list()
            if limit:
                data = data[offset:offset + limit]
            
            return jsonify({
                'path': csv_path,
                'source': 'config' if csv_path == app.config.get('CSV_PATH') else 'auto-detect',
                'total': len(parser.data),
                'data': data,
                'statistics': parser.get_statistics()
            })
        except Exception as e:
            logger.error(f"Errore parsing CSV: {e}")
            return jsonify({'error': str(e), 'data': [], 'statistics': {}}), 500
    
    @app.route('/api/predictions/json')
    def api_predictions_json():
        """Previsioni e metriche dal JSON (fonte secondaria per metriche)"""
        config_dir = Path(app.config.get('CONFIG_DIR', '.'))
        json_dir = app.config.get('JSON_DIR')
        
        # Cerca il JSON nella directory specificata dal config
        json_path = None
        
        if json_dir and os.path.exists(json_dir):
            json_files = list(Path(json_dir).glob('predictions.json'))
            if json_files:
                json_path = str(json_files[0])
        
        # Fallback se non trovato
        if not json_path:
            for subdir in ['output', '.', 'data']:
                pattern_dir = config_dir / subdir
                if pattern_dir.exists():
                    json_files = list(pattern_dir.glob('predictions.json'))
                    if json_files:
                        json_path = str(json_files[0])
                        break
        
        if not json_path:
            return jsonify({'error': 'JSON previsioni non trovato'}), 404
        
        try:
            parser = PredictionsJSONParser(json_path)
            
            # Paginazione per predictions
            limit = request.args.get('limit', type=int)
            offset = request.args.get('offset', 0, type=int)
            
            return jsonify({
                'path': json_path,
                'source': 'config' if json_dir and json_path.startswith(json_dir) else 'auto-detect',
                'metadata': parser.get_metadata(),
                'metrics': parser.get_metrics(),
                'predictions_count': parser.get_predictions_count(),
                'predictions': parser.get_predictions(limit, offset),
                'signals_summary': parser.get_signals_summary()
            })
        except Exception as e:
            logger.error(f"Errore parsing JSON: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/metrics')
    def api_metrics():
        """Solo le metriche (endpoint veloce)"""
        config_dir = Path(app.config.get('CONFIG_DIR', '.'))
        
        json_path = None
        for subdir in ['output', '.', 'data']:
            pattern_dir = config_dir / subdir
            if pattern_dir.exists():
                json_files = list(pattern_dir.glob('predictions.json'))
                if json_files:
                    json_path = str(json_files[0])
                    break
        
        if not json_path:
            return jsonify({'error': 'Metriche non disponibili'}), 404
        
        try:
            parser = PredictionsJSONParser(json_path)
            return jsonify({
                'metadata': parser.get_metadata(),
                'metrics': parser.get_metrics(),
                'signals_summary': parser.get_signals_summary()
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    # ═══════════════════════════════════════════════════════════════════════
    # ERROR HANDLERS
    # ═══════════════════════════════════════════════════════════════════════
    
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'Risorsa non trovata'}), 404
    
    @app.errorhandler(500)
    def server_error(e):
        return jsonify({'error': 'Errore interno del server'}), 500
    
    return app

# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Entry point principale"""
    
    parser = argparse.ArgumentParser(
        description='PROFETA Universal Dashboard - Web Monitoring Interface',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi:
  python server.py --config ../config-lstm.ini
  python server.py --config /path/to/config.ini --port 8080
  python server.py --debug
        """
    )
    
    parser.add_argument(
        '--config', '-c',
        type=str,
        default=None,
        help='Path al file config-lstm.ini di PROFETA'
    )
    
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=5000,
        help='Porta HTTP (default: 5000)'
    )
    
    parser.add_argument(
        '--host', '-H',
        type=str,
        default='127.0.0.1',
        help='Host binding (default: 127.0.0.1)'
    )
    
    parser.add_argument(
        '--debug', '-d',
        action='store_true',
        help='Abilita modalità debug'
    )
    
    args = parser.parse_args()
    
    # Banner
    print()
    print("╔═══════════════════════════════════════════════════════════════════════════╗")
    print("║                                                                           ║")
    print("║     ██████╗ ██████╗  ██████╗ ███████╗███████╗████████╗ █████╗             ║")
    print("║     ██╔══██╗██╔══██╗██╔═══██╗██╔════╝██╔════╝╚══██╔══╝██╔══██╗            ║")
    print("║     ██████╔╝██████╔╝██║   ██║█████╗  █████╗     ██║   ███████║            ║")
    print("║     ██╔═══╝ ██╔══██╗██║   ██║██╔══╝  ██╔══╝     ██║   ██╔══██║            ║")
    print("║     ██║     ██║  ██║╚██████╔╝██║     ███████╗   ██║   ██║  ██║            ║")
    print("║     ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚══════╝   ╚═╝   ╚═╝  ╚═╝            ║")
    print("║                                                                           ║")
    print("║                    UNIVERSAL DASHBOARD v" + VERSION + "                            ║")
    print("║                      BilliDynamics™ 2026                                  ║")
    print("║                                                                           ║")
    print("╚═══════════════════════════════════════════════════════════════════════════╝")
    print()
    
    # Crea app
    app = create_app(config_path=args.config)
    
    # Info avvio
    logger.info(f"Config: {args.config or 'Auto-detect'}")
    logger.info(f"Server: http://{args.host}:{args.port}")
    logger.info(f"Debug: {'Abilitato' if args.debug else 'Disabilitato'}")
    print()
    print("─" * 75)
    print()
    
    # Avvia server
    app.run(
        host=args.host,
        port=args.port,
        debug=args.debug,
        threaded=True
    )

if __name__ == '__main__':
    main()
