function(doc, req) {
  if(doc.status == "verification" || doc.status == "pending.dissolution") {return true;}
    return false;
}
