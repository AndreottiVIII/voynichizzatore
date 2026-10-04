# Voynichizzatore

Prende un testo qualsiasi e una parola chiave e scrive un manoscritto "alla Voynich", in EVA (l'alfabeto con cui si
trascrive il manoscritto Voynich, Beinecke MS 408). Con la stessa chiave il testo torna fuori esatto.

    python voynichizzatore.py codifica testo.txt --chiave "una frase lunga" --uscita manoscritto.txt
    python voynichizzatore.py decodifica manoscritto.txt --chiave "una frase lunga" --uscita testo.txt
    python voynichizzatore.py vuoto --chiave "una frase lunga" --uscita manoscritto.txt

Serve Python 3.12 con `numpy`, `scipy` e `scikit-learn` (`pip install -r requirements.txt`). Scrivere un manoscritto
prende un paio di minuti, rileggerlo pochi secondi.

## Che cosa esce

- Un libro intero di 207 pagine e circa 4.200 righe, qualunque sia la lunghezza del testo; una riga del file per riga del
  manoscritto, `<pagina.riga> parole.separate.da.punti`, con `@` davanti alle righe che aprono un paragrafo.
- È testo in EVA, non un'immagine delle pagine.
- Ci stanno circa 80.000 bit, cioè circa 20.000 caratteri di testo dopo la compressione. Se il testo è più lungo il
  programma lo dice. Se è più corto, il resto del libro è riempito in modo che non si veda dove finisce il messaggio.

## Come funziona, in breve

- **Le parole di ogni pagina** vengono dal lessico della sezione del Voynich a cui la pagina corrisponde, con una
  preferenza per certi segni ("carattere" della pagina) presa da un'altra pagina; in più ci sono parole nuove, inventate
  con la forma delle parole che nel Voynich compaiono una volta sola.
- **Il messaggio** (compresso e cifrato con la chiave) decide quante volte compare ogni parola nota in ogni pagina. Non
  c'è corrispondenza fra le parole del manoscritto e quelle del testo: non c'è niente da tradurre parola per parola.
- **La disposizione** delle parole nelle righe segue la forma delle parole (inizio e fine riga, prime righe dei
  paragrafi) e pochi legami deboli fra parole vicine. Non porta informazione: per rileggere il messaggio bastano le
  parole di ogni pagina e la chiave.
- **La gabbia** di ogni pagina (quante righe, quante parole per riga, dove iniziano i paragrafi) è estratta dalle
  statistiche del Voynich: nessuna pagina ha la gabbia di una pagina vera.

## Quanto somiglia al Voynich (misure fatte, con i loro limiti)

Misurato nascondendo lo stesso testo latino con 12 chiavi diverse. I "giudici" sono due classificatori che provano a
distinguere le pagine generate da quelle vere guardando circa 220 statistiche di pagina: 0,5 vuol dire che tirano a
indovinare, 1 che non sbagliano mai.

| misura | valore |
|---|---|
| giudice 1 (statistiche di segni, parole, righe) | 0,56 ± 0,01 |
| giudice 2 (in più: coppie di parole, posizione nella riga, prime righe, profilo della pagina) | 0,60 ± 0,01 |
| pagella a 18 proprietà del testo (17 raggiungibili: una la perde anche il Voynich misurato allo stesso modo) | 15 |
| altre 8 proprietà | circa 6 |
| il testo torna esatto | 12 volte su 12 |
| chiave sbagliata respinta | 12 volte su 12 |

Un manoscritto con un messaggio e uno senza non si distinguono fra loro con queste misure.

**Che cosa NON vuol dire.** Non è "indistinguibile dal Voynich":

- il secondo giudice lo riconosce ancora un po' (circa una chiave su due dà un manoscritto sopra 0,60);
- alcune proprietà note non tornano mai: il profilo di pagina, le scelte di grafia concordi nella riga misurate su 12
  classi, la somiglianza fra parole della stessa riga (un po' troppo alta);
- il modello è stato regolato sulle stesse statistiche che questi giudici guardano; un giudice costruito in modo
  indipendente non è stato provato;
- quasi tutte le parole sono parole del Voynich: chi conosce il programma capisce che il manoscritto è fatto con il
  programma. Quello che non può capire è se dentro c'è un messaggio.

## Sicurezza

- La chiave passa per scrypt, il testo è cifrato con un flusso SHAKE-256 e porta un'etichetta HMAC-SHA256: con la chiave
  sbagliata il programma risponde "chiave errata".
- Sono mattoni standard, ma l'insieme **non è stato verificato da un esperto**: non usarlo per segreti veri. La sicurezza
  dipende dalla chiave: una frase lunga, non una parola del dizionario.
- Scrittura e rilettura usano calcoli in virgola mobile: usa la stessa versione del programma per scrivere e per
  rileggere. La rilettura su un computer diverso da quello che ha scritto il manoscritto non è stata ancora provata.

## Fonti

- **Testo del Voynich** (`voynich_zl3b.json`): dalla trascrizione ZL di René Zandbergen e Gabriel Landini, versione 3b del
  13/05/2025, pubblicata su https://www.voynich.nu/ , dove le trascrizioni sono dichiarate di pubblico dominio e messe a
  disposizione con licenza Creative Commons CC0. Qui c'è solo il testo corrente in paragrafi, con le parole leggibili.
- Il manoscritto è conservato alla Beinecke Rare Book and Manuscript Library dell'Università di Yale (MS 408).

## Licenza

Il programma è sotto licenza MIT (file `LICENSE`). Il testo del Voynich in `voynich_zl3b.json` è di pubblico dominio (CC0).

## Prova di rilettura su un altro computer

    python prova.py

Rilegge il manoscritto di prova incluso (scritto su un altro computer), poi ne scrive uno nuovo e lo rilegge. Alla fine
stampa tre righe con l'esito: se la prima dice "sì", un manoscritto scritto altrove si rilegge anche qui.
