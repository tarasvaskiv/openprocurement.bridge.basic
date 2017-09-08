function(doc, req) {
  if(doc.status == "verification" || doc.status == "dissolved") {return true;}
    return false;
}
