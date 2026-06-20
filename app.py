from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Data sementara (Simulasi Database)
DATA_REPARASI = {
    "REP-001": {"nama": "Dean", "tipe": "Sepatu Sneaker", "kendala": "Sol lepas", "status": "Diproses"},
    "REP-002": {"nama": "Diana", "tipe": "Tas Kulit", "kendala": "Resleting rusak", "status": "Selesai"},
    "REP-003": {"nama": "Keandra", "tipe": "Sepatu Running", "kendala": "Reglue", "status": "Antre"},
    "REP-004": {"nama": "Bella", "tipe": "Tas Ransel", "kendala": "Repaint", "status": "Diproses"},


}

@app.route('/')
def index():
    # Mengambil parameter pencarian jika ada
    search_id = request.args.get('search_id', '').strip().upper()
    hasil_pencarian = None
    pesan_error = None

    if search_id:
        if search_id in DATA_REPARASI:
            hasil_pencarian = DATA_REPARASI[search_id]
            hasil_pencarian['id'] = search_id
        else:
            pesan_error = "Nomor Resi tidak ditemukan!"

    return render_template('index.html', data=DATA_REPARASI, hasil=hasil_pencarian, error=pesan_error, search_id=search_id)

@app.route('/tambah', methods=['POST'])
def tambah_reparasi():
    nama = request.form.get('nama')
    tipe = request.form.get('tipe')
    kendala = request.form.get('kendala')
    
    # Generate ID Baru
    next_id = f"REP-00{len(DATA_REPARASI) + 1}"
    
    DATA_REPARASI[next_id] = {
        "nama": nama,
        "tipe": tipe,
        "kendala": kendala,
        "status": "Antre"
    }
    
    return redirect(url_for('index'))

@app.route('/update/<id_resi>/<status>')
def update_status(id_resi, status):
    if id_resi in DATA_REPARASI:
        DATA_REPARASI[id_resi]['status'] = status
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)