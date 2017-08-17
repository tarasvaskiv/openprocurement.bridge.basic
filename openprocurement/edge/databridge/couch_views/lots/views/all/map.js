function(doc) {
    if(doc.doc_type == 'Lot') {
        emit(doc.planID, null);
    }
}
