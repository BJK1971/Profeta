# Le 6 Fasi (STEP) della Pipeline di Addestramento di Profeta

Il file [profeta-universal.py](file:///c:/work/gitrepo/Profeta/profeta-universal.py) esegue una complessa pipeline di addestramento e validazione per garantire che l'Ensemble di modelli predittivi (LSTM e BiLSTM) sia robusto e non subisca contaminazioni di dati dal futuro (il temuto *data leakage*).

Di seguito il dettaglio tecnico e concettuale di ogni singola fase che puoi osservare nei log di esecuzione.

---

### STEP 1: Fitting scaler on TRAIN only (no data leakage)
In questa prima fase, l'algoritmo analizza **esclusivamente i dati storici passati** (il set di TRAIN) per calcolare la scala dei prezzi (valori minimi e massimi). Questo è un passaggio fondamentale: se l'AI "spiasse" i dati di convalida o di test futuri per calcolare la media del mercato, barerebbe. Fissando i parametri matematici solo sul passato, simuliamo le esatte condizioni di "cecità" verso il futuro in cui il bot si troverà a operare.

### STEP 2: Transforming all sets with TRAIN-fitted scaler
Utilizzando i parametri di ridimensionamento scoperti allo Step 1, l'intero dataset (passato, calibrazione e futuro previsto) viene "normalizzato" (compresso tipicamente in un range tra 0 e 1, o tra -1 e 1). Questa trasformazione è obbligatoria per far "digerire" le variazioni di prezzo in modo uniforme e veloce alle reti neurali profonde.

### STEP 3: Training model on TRAIN only
Questo è il cuore computazionale del sistema. I modelli *LSTM* (Long Short-Term Memory) e *BiLSTM* iniziano il loro addestramento ciclico studiando i pattern grafici e le memorie di prezzo a lungo termine. Anche qui, l'apprendimento avviene **rigorosamente sulla porzione storicizzata** dei dati. Il sistema implementa meccanismi come l'Early Stopping per interrompere il training qualora la rete smetta di generalizzare e inizi a imparare il rumore di fondo a memoria (*overfitting*).

### STEP 4: Calibrating conformal on CALIB only (out-of-sample, asymmetric)
Qui risiede l'intelligenza probabilistica del motore. Anziché restituire una previsione assoluta su cui è impossibile fare affidamento cieco, Profeta effettua un test su una porzione di dati **mai vista in addestramento** (il set CALIB). L'obiettivo è calibrare un "involucro di errore" (Conformal Prediction) che definisca statisticamente le fasce di confidenza (es. 50%, 90% e 95%) del movimento futuro. È definito "asimmetrico" perché il calcolo separa la volatilità dei crolli improvvisi da quella delle salite costanti.

### STEP 5: Evaluating metrics on TEST only (truly held-out)
La prova della verità. Viene preso l'ultimo pacchetto di dati, il set di TEST "super-segreto", completamente isolato fin dall'inizio. L'Ensemble matematico esegue le sue previsioni su questi dati per farsi valutare prima di essere approvato per il live trading. Vengono calcolati l'Accuratezza Direzionale (es. 96%), l'R² e il MAE (Mean Absolute Error).

### STEP 6: Verifying coverage on TEST (out-of-sample guarantee)
In quest'ultima fase, il sistema fa un controllo incrociato sulle bande di confidenza generate allo Step 4. Verifica matematicamente sul set di TEST se l'involucro di incertezza (es. la fascia al 90%) è effettivamente riuscito a contenere il vero prezzo futuro il 90% delle volte. Se il *coverage* viene garantito, l'algoritmo incassa la validazione probabilistica e si prepara a sfornare le vere proiezioni sul mercato per il tuo trading bot.
