function(doc) {
    if(doc.doc_type == 'Auction') {
        emit(doc.planID, null);
    }
}
