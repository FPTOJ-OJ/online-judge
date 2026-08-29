

'use strict';
{
  const globals = this;
  const django = globals.django || (globals.django = {});

  
  django.pluralidx = function(n) {
    const v = (n==1 ? 0 : (n==0 || (n%100>0 && n%100<20)) ? 1 : 2);
    if (typeof v === 'boolean') {
      return v ? 1 : 0;
    } else {
      return v;
    }
  };
  

  /* gettext library */

  django.catalog = django.catalog || {};
  
  const newcatalog = {
    "%(cnt)d submission in %(year)d": [
      "%(cnt)d b\u00e0i g\u1eedi trong n\u0103m %(year)d",
      "",
      ""
    ],
    "%(cnt)d submission in the last year": [
      "%(cnt)d b\u00e0i g\u1eedi trong m\u1ed9t n\u0103m tr\u01b0\u1edbc",
      "",
      ""
    ],
    "%(cnt)d submission on %(date)s": [
      "%(cnt)d b\u00e0i g\u1eedi trong ng\u00e0y %(date)s",
      "",
      ""
    ],
    "%(cnt)d total submission": [
      "%(cnt)d t\u1ed5ng s\u1ed1 b\u00e0i \u0111\u00e3 g\u1eedi",
      "",
      ""
    ],
    "%(sel)s of %(cnt)s selected": [
      "%(sel)s din %(cnt)s selectate",
      "%(sel)s din %(cnt)s selectate",
      "de %(sel)s din %(cnt)s selectate"
    ],
    "6 a.m.": "6 a.m.",
    "6 p.m.": "6 p.m.",
    "April": "Aprilie",
    "August": "August",
    "Available %s": "%s disponibil",
    "Cancel": "Anuleaz\u0103",
    "Choose": "Alege",
    "Choose a Date": "Alege o dat\u0103",
    "Choose a Time": "Alege o or\u0103",
    "Choose a time": "Alege o or\u0103",
    "Choose all": "Alege toate",
    "Chosen %s": "%s alese",
    "Click to choose all %s at once.": "Click pentru a alege toate %s.",
    "Click to remove all chosen %s at once.": "Click pentru a elimina toate %s alese.",
    "December": "Decembrie",
    "Edit points vote (%s)": "S\u1eeda \u0111i\u1ec3m vote (%s)",
    "February": "Februarie",
    "Filter": "Filtru",
    "Hide": "Ascunde",
    "January": "Ianuarie",
    "July": "Iulie",
    "June": "Iunie",
    "March": "Martie",
    "May": "Mai",
    "Midnight": "Miezul nop\u021bii",
    "Noon": "Amiaz\u0103",
    "Note: You are %s hour ahead of server time.": [
      "Not\u0103: Sunte\u021bi cu %s or\u0103 \u00eenaintea orei serverului.",
      "Not\u0103: Sunte\u021bi cu %s ore \u00eenaintea orei serverului.",
      "Not\u0103: Sunte\u021bi cu %s de ore \u00eenaintea orei serverului."
    ],
    "Note: You are %s hour behind server time.": [
      "Not\u0103: Sunte\u021bi cu %s or\u0103 \u00een urma orei serverului.",
      "Not\u0103: Sunte\u021bi cu %s ore \u00een urma orei serverului.",
      "Not\u0103: Sunte\u021bi cu %s de ore \u00een urma orei serverului."
    ],
    "November": "Noiembrie",
    "Now": "Acum",
    "Number of votes for this point value": "S\u1ed1 l\u01b0\u1ee3ng b\u00ecnh ch\u1ecdn cho \u0111i\u1ec3m n\u00e0y",
    "October": "Octombrie",
    "Remove": "Elimin\u0103",
    "Remove all": "Elimin\u0103 toate",
    "September": "Septembrie",
    "Show": "Arat\u0103",
    "This is the list of available %s. You may choose some by selecting them in the box below and then clicking the \"Choose\" arrow between the two boxes.": "Aceasta este o list\u0103 cu %s disponibile. Le pute\u021bi alege select\u00e2nd mai multe in chenarul de mai jos \u0219i ap\u0103s\u00e2nd pe s\u0103geata \"Alege\" dintre cele dou\u0103 chenare.",
    "This is the list of chosen %s. You may remove some by selecting them in the box below and then clicking the \"Remove\" arrow between the two boxes.": "Aceasta este lista de %s alese. Pute\u021bi elimina din ele select\u00e2ndu-le in chenarul de mai jos \u0219i apasand pe s\u0103geata \"Elimin\u0103\" dintre cele dou\u0103 chenare.",
    "Today": "Ast\u0103zi",
    "Tomorrow": "M\u00e2ine",
    "Type into this box to filter down the list of available %s.": "Scrie \u00een acest chenar pentru a filtra lista de %s disponibile.",
    "Unable to cast vote: %s": "Kh\u00f4ng th\u1ec3 s\u1eeda \u0111i\u1ec3m: %s",
    "Unable to delete vote: %s": "Kh\u00f4ng th\u1ec3 s\u1eeda \u0111i\u1ec3m: %s",
    "Vote on problem points": "B\u00ecnh ch\u1ecdn \u0111i\u1ec3m c\u1ee7a b\u00e0i t\u1eadp",
    "Yesterday": "Ieri",
    "You have selected an action, and you haven\u2019t made any changes on individual fields. You\u2019re probably looking for the Go button rather than the Save button.": "Ai selectat o ac\u021biune \u0219i nu ai f\u0103cut modific\u0103ri. Probabil c\u0103 dore\u0219ti butonul de Go mai putin cel de Salveaz\u0103.",
    "You have selected an action, but you haven\u2019t saved your changes to individual fields yet. Please click OK to save. You\u2019ll need to re-run the action.": "Ai selectat o ac\u021biune dar nu ai salvat modific\u0103rile f\u0103cute \u00een c\u00e2mpuri individuale. Te rug\u0103m apasa Ok pentru a salva. Va trebui sa reiei ac\u021biunea.",
    "You have unsaved changes on individual editable fields. If you run an action, your unsaved changes will be lost.": "Ave\u0163i modific\u0103ri nesalvate \u00een c\u00eempuri individuale editabile. Dac\u0103 executa\u0163i o ac\u021biune, modific\u0103rile nesalvate vor fi pierdute.",
    "abbrev. month April\u0004Apr": "Th\u00e1ng T\u01b0",
    "abbrev. month August\u0004Aug": "Th\u00e1ng T\u00e1m",
    "abbrev. month December\u0004Dec": "Th\u00e1ng M\u01b0\u1eddi Hai",
    "abbrev. month February\u0004Feb": "Th\u00e1ng Hai",
    "abbrev. month January\u0004Jan": "Th\u00e1ng M\u1ed9t",
    "abbrev. month July\u0004Jul": "Th\u00e1ng B\u1ea3y",
    "abbrev. month June\u0004Jun": "Th\u00e1ng S\u00e1u",
    "abbrev. month March\u0004Mar": "Th\u00e1ng Ba",
    "abbrev. month May\u0004May": "Th\u00e1ng N\u0103m",
    "abbrev. month November\u0004Nov": "Th\u00e1ng M\u01b0\u1eddi M\u1ed9t",
    "abbrev. month October\u0004Oct": "Th\u00e1ng M\u01b0\u1eddi",
    "abbrev. month September\u0004Sep": "Th\u00e1ng Ch\u00edn",
    "one letter Friday\u0004F": "V",
    "one letter Monday\u0004M": "L",
    "one letter Saturday\u0004S": "S",
    "one letter Sunday\u0004S": "D",
    "one letter Thursday\u0004T": "J",
    "one letter Tuesday\u0004T": "M",
    "one letter Wednesday\u0004W": "M",
    "past year": "m\u1ed9t n\u0103m tr\u01b0\u1edbc",
    "time format with day\u0004%d day %h:%m:%s": [
      "%d zi %h:%m:%s",
      "%d zi %h:%m:%s",
      "%d zile %h:%m:%s"
    ],
    "time format without day\u0004%h:%m:%s": "%h:%m:%s"
  };
  for (const key in newcatalog) {
    django.catalog[key] = newcatalog[key];
  }
  

  if (!django.jsi18n_initialized) {
    django.gettext = function(msgid) {
      const value = django.catalog[msgid];
      if (typeof value === 'undefined') {
        return msgid;
      } else {
        return (typeof value === 'string') ? value : value[0];
      }
    };

    django.ngettext = function(singular, plural, count) {
      const value = django.catalog[singular];
      if (typeof value === 'undefined') {
        return (count == 1) ? singular : plural;
      } else {
        return value.constructor === Array ? value[django.pluralidx(count)] : value;
      }
    };

    django.gettext_noop = function(msgid) { return msgid; };

    django.pgettext = function(context, msgid) {
      let value = django.gettext(context + '\x04' + msgid);
      if (value.includes('\x04')) {
        value = msgid;
      }
      return value;
    };

    django.npgettext = function(context, singular, plural, count) {
      let value = django.ngettext(context + '\x04' + singular, context + '\x04' + plural, count);
      if (value.includes('\x04')) {
        value = django.ngettext(singular, plural, count);
      }
      return value;
    };

    django.interpolate = function(fmt, obj, named) {
      if (named) {
        return fmt.replace(/%\(\w+\)s/g, function(match){return String(obj[match.slice(2,-2)])});
      } else {
        return fmt.replace(/%s/g, function(match){return String(obj.shift())});
      }
    };


    /* formatting library */

    django.formats = {
    "DATETIME_FORMAT": "j F Y, H:i",
    "DATETIME_INPUT_FORMATS": [
      "%d.%m.%Y, %H:%M",
      "%d.%m.%Y, %H:%M:%S",
      "%d.%B.%Y, %H:%M",
      "%d.%B.%Y, %H:%M:%S",
      "%Y-%m-%d %H:%M:%S",
      "%Y-%m-%d %H:%M:%S.%f",
      "%Y-%m-%d %H:%M",
      "%Y-%m-%d"
    ],
    "DATE_FORMAT": "j F Y",
    "DATE_INPUT_FORMATS": [
      "%d.%m.%Y",
      "%d.%b.%Y",
      "%d %B %Y",
      "%A, %d %B %Y",
      "%Y-%m-%d"
    ],
    "DECIMAL_SEPARATOR": ",",
    "FIRST_DAY_OF_WEEK": 1,
    "MONTH_DAY_FORMAT": "j F",
    "NUMBER_GROUPING": 3,
    "SHORT_DATETIME_FORMAT": "d.m.Y, H:i",
    "SHORT_DATE_FORMAT": "d.m.Y",
    "THOUSAND_SEPARATOR": ".",
    "TIME_FORMAT": "H:i",
    "TIME_INPUT_FORMATS": [
      "%H:%M",
      "%H:%M:%S",
      "%H:%M:%S.%f"
    ],
    "YEAR_MONTH_FORMAT": "F Y"
  };

    django.get_format = function(format_type) {
      const value = django.formats[format_type];
      if (typeof value === 'undefined') {
        return format_type;
      } else {
        return value;
      }
    };

    /* add to global namespace */
    globals.pluralidx = django.pluralidx;
    globals.gettext = django.gettext;
    globals.ngettext = django.ngettext;
    globals.gettext_noop = django.gettext_noop;
    globals.pgettext = django.pgettext;
    globals.npgettext = django.npgettext;
    globals.interpolate = django.interpolate;
    globals.get_format = django.get_format;

    django.jsi18n_initialized = true;
  }
};

