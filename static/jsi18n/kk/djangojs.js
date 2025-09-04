

'use strict';
{
  const globals = this;
  const django = globals.django || (globals.django = {});

  
  django.pluralidx = function(n) {
    const v = (n != 1);
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
      "%(cnt)d \u0442\u0430\u043f\u0441\u044b\u0440\u044b\u043b\u044b\u043c %(year)d \u0436\u044b\u043b\u044b",
      "%(cnt)d \u0442\u0430\u043f\u0441\u044b\u0440\u044b\u043b\u044b\u043c %(year)d \u0436\u044b\u043b\u044b"
    ],
    "%(cnt)d submission in the last year": [
      "%(cnt)d \u0442\u0430\u043f\u0441\u044b\u0440\u044b\u043b\u044b\u043c c\u043e\u04a3\u0493\u044b \u0436\u044b\u043b\u0434\u0430",
      "%(cnt)d \u0442\u0430\u043f\u0441\u044b\u0440\u044b\u043b\u044b\u043c c\u043e\u04a3\u0493\u044b \u0436\u044b\u043b\u0434\u0430"
    ],
    "%(cnt)d submission on %(date)s": [
      "%(cnt)d \u0442\u0430\u043f\u0441\u044b\u0440\u044b\u043b\u044b\u043c %(date)s \u0436\u044b\u043b\u044b",
      "%(cnt)d \u0442\u0430\u043f\u0441\u044b\u0440\u044b\u043b\u044b\u043c %(date)s \u0436\u044b\u043b\u044b"
    ],
    "%(cnt)d total submission": [
      "%(cnt)d \u0431\u0430\u0440\u043b\u044b\u049b \u0442\u0430\u043f\u0441\u044b\u0440\u044b\u043b\u044b\u043c",
      "%(cnt)d \u0431\u0430\u0440\u043b\u044b\u049b \u0442\u0430\u043f\u0441\u044b\u0440\u044b\u043b\u044b\u043c"
    ],
    "%(sel)s of %(cnt)s selected": [
      "%(cnt)s-\u04a3 %(sel)s-\u044b(\u0456) \u0442\u0430\u04a3\u0434\u0430\u043b\u0434\u044b",
      "%(cnt)s-\u04a3 %(sel)s-\u044b(\u0456) \u0442\u0430\u04a3\u0434\u0430\u043b\u0434\u044b"
    ],
    "6 a.m.": "06",
    "6 p.m.": "6 gi\u1edd chi\u1ec1u",
    "April": "Th\u00e1ng T\u01b0",
    "August": "Th\u00e1ng T\u00e1m",
    "Available %s": "%s \u0431\u0430\u0440",
    "Cancel": "\u0411\u043e\u043b\u0434\u044b\u0440\u043c\u0430\u0443",
    "Choose": "Ch\u1ecdn",
    "Choose a Date": "Ch\u1ecdn Ng\u00e0y",
    "Choose a Time": "Ch\u1ecdn Th\u1eddi gian",
    "Choose a time": "\u0423\u0430\u049b\u044b\u0442\u0442\u044b \u0442\u0430\u04a3\u0434\u0430",
    "Choose all": "Ch\u1ecdn t\u1ea5t c\u1ea3",
    "Chosen %s": "Ch\u1ecdn %s",
    "Click to choose all %s at once.": "Click \u0111\u1ec3 ch\u1ecdn t\u1ea5t c\u1ea3 %s .",
    "Click to remove all chosen %s at once.": "Click \u0111\u1ec3 b\u1ecf ch\u1ecdn t\u1ea5t c\u1ea3 %s",
    "December": "Th\u00e1ng M\u01b0\u1eddi Hai",
    "Edit points vote (%s)": "\u04b0\u043f\u0430\u0439\u043b\u0430\u0440 \u0434\u0430\u0443\u044b\u0441\u044b\u043d \u04e9\u0437\u0433\u0435\u0440\u0442\u0443 (%s)",
    "February": "Th\u00e1ng Hai",
    "Filter": "\u0421\u04af\u0437\u0433\u0456\u0448",
    "Hide": "\u0416\u0430\u0441\u044b\u0440\u0443",
    "January": "Th\u00e1ng M\u1ed9t",
    "July": "Th\u00e1ng B\u1ea3y",
    "June": "Th\u00e1ng S\u00e1u",
    "March": "Th\u00e1ng Ba",
    "May": "Th\u00e1ng N\u0103m",
    "Midnight": "\u0422\u04af\u043d \u0436\u0430\u0440\u044b\u043c",
    "Noon": "\u0422\u0430\u043b\u0442\u04af\u0441",
    "Note: You are %s hour ahead of server time.": [
      "L\u01b0u \u00fd: Hi\u1ec7n t\u1ea1i b\u1ea1n \u0111ang th\u1ea5y th\u1eddi gian tr\u01b0\u1edbc %s gi\u1edd so v\u1edbi th\u1eddi gian m\u00e1y ch\u1ee7.",
      ""
    ],
    "Note: You are %s hour behind server time.": [
      "L\u01b0u \u00fd: Hi\u1ec7n t\u1ea1i b\u1ea1n \u0111ang th\u1ea5y th\u1eddi gian sau %s gi\u1edd so v\u1edbi th\u1eddi gian m\u00e1y ch\u1ee7.",
      ""
    ],
    "November": "Th\u00e1ng M\u01b0\u1eddi M\u1ed9t",
    "Now": "\u049a\u0430\u0437\u0456\u0440",
    "Number of votes for this point value": "\u041e\u0441\u044b \u04b1\u043f\u0430\u0439 \u043c\u04d9\u043d\u0456\u043d\u0435 \u0431\u0435\u0440\u0456\u043b\u0433\u0435\u043d \u0434\u0430\u0443\u044b\u0441\u0442\u0430\u0440 \u0441\u0430\u043d\u044b",
    "October": "Th\u00e1ng M\u01b0\u1eddi",
    "Remove": "\u04e8\u0448\u0456\u0440\u0443(\u0436\u043e\u044e)",
    "Remove all": "Xo\u00e1 t\u1ea5t c\u1ea3",
    "September": "Th\u00e1ng Ch\u00edn",
    "Show": "\u041a\u04e9\u0440\u0441\u0435\u0442\u0443",
    "This is the list of available %s. You may choose some by selecting them in the box below and then clicking the \"Choose\" arrow between the two boxes.": "Danh s\u00e1ch c\u00e1c l\u1ef1a ch\u1ecdn \u0111ang c\u00f3 %s. B\u1ea1n c\u00f3 th\u1ec3 ch\u1ecdn b\u1eb1ng b\u00e1ch click v\u00e0o m\u0169i t\u00ean \"Ch\u1ecdn\" n\u1eb1m gi\u1eefa hai h\u1ed9p.",
    "This is the list of chosen %s. You may remove some by selecting them in the box below and then clicking the \"Remove\" arrow between the two boxes.": "Danh s\u00e1ch b\u1ea1n \u0111\u00e3 ch\u1ecdn %s. B\u1ea1n c\u00f3 th\u1ec3 b\u1ecf ch\u1ecdn b\u1eb1ng c\u00e1ch click v\u00e0o m\u0169i t\u00ean \"Xo\u00e1\" n\u1eb1m gi\u1eefa hai \u00f4.",
    "Today": "\u0411\u04af\u0433\u0456\u043d",
    "Tomorrow": "\u0415\u0440\u0442\u0435\u04a3",
    "Type into this box to filter down the list of available %s.": "B\u1ea1n h\u00e3y nh\u1eadp v\u00e0o \u00f4 n\u00e0y \u0111\u1ec3 l\u1ecdc c\u00e1c danh s\u00e1ch sau %s.",
    "Unable to cast vote: %s": "\u0414\u0430\u0443\u044b\u0441 \u0431\u0435\u0440\u0443 \u043c\u04af\u043c\u043a\u0456\u043d \u0435\u043c\u0435\u0441: %s",
    "Unable to delete vote: %s": "\u0411\u0435\u0440\u0456\u043b\u0433\u0435\u043d \u0434\u0430\u0443\u044b\u0441\u0442\u044b \u0436\u043e\u044e \u043c\u04af\u043c\u043a\u0456\u043d \u0435\u043c\u0435\u0441: %s",
    "Vote on problem points": "\u0415\u0441\u0435\u043f \u04b1\u043f\u0430\u0439\u043b\u0430\u0440\u044b\u043d\u0430 \u0434\u0430\u0443\u044b\u0441 \u0431\u0435\u0440\u0456\u04a3\u0456\u0437",
    "Yesterday": "\u041a\u0435\u0448\u0435",
    "You have selected an action, and you haven't made any changes on individual fields. You're probably looking for the Go button rather than the Save button.": "\u0421\u0456\u0437 \u0421\u0430\u049b\u0442\u0430\u0443 \u0431\u0430\u0442\u044b\u0440\u043c\u0430\u0441\u044b\u043d\u0430 \u049b\u0430\u0440\u0430\u0493\u0430\u043d\u0434\u0430, Go(\u0410\u043b\u0493\u0430) \u0431\u0430\u0442\u044b\u0440\u043c\u0430\u0441\u044b\u043d \u0456\u0437\u0434\u0435\u043f \u043e\u0442\u044b\u0440\u0493\u0430\u043d \u0431\u043e\u043b\u0430\u0440\u0441\u044b\u0437, \u0441\u0435\u0431\u0435\u0431\u0456 \u0435\u0448\u049b\u0430\u043d\u0434\u0430\u0439 \u04e9\u0437\u0433\u0435\u0440\u0456\u0441 \u0436\u0430\u0441\u0430\u043c\u0430\u0439, \u04d9\u0440\u0435\u043a\u0435\u0442 \u0436\u0430\u0441\u0430\u0434\u044b\u04a3\u044b\u0437.",
    "You have selected an action, and you haven\u2019t made any changes on individual fields. You\u2019re probably looking for the Go button rather than the Save button.": "B\u1ea1n \u0111\u00e3 ch\u1ecdn m\u1ed9t h\u00e0nh \u0111\u1ed9ng v\u00e0 b\u1ea1n \u0111\u00e3 kh\u00f4ng th\u1ef1c hi\u1ec7n b\u1ea5t k\u1ef3 thay \u0111\u1ed5i n\u00e0o tr\u00ean c\u00e1c tr\u01b0\u1eddng. C\u00f3 l\u1ebd b\u1ea1n n\u00ean b\u1ea5m n\u00fat \u0110i \u0111\u1ebfn h\u01a1n l\u00e0 n\u00fat L\u01b0u l\u1ea1i.",
    "You have selected an action, but you haven't saved your changes to individual fields yet. Please click OK to save. You'll need to re-run the action.": "\u0421\u0456\u0437 \u04e9\u0437 \u04e9\u0437\u0433\u0435\u0440\u0456\u0441\u0442\u0435\u0440\u0456\u04a3\u0456\u0437\u0434\u0456 \u0441\u0430\u049b\u0442\u0430\u043c\u0430\u0439, \u04d9\u0440\u0435\u043a\u0435\u0442 \u0436\u0430\u0441\u0430\u0434\u044b\u04a3\u044b\u0437. \u04e8\u0442\u0456\u043d\u0456\u0448, \u0441\u0430\u049b\u0442\u0430\u0443 \u04af\u0448\u0456\u043d \u041e\u041a \u0431\u0430\u0442\u044b\u0440\u043c\u0430\u0441\u044b\u043d \u0431\u0430\u0441\u044b\u04a3\u044b\u0437 \u0436\u04d9\u043d\u0435 \u04e9\u0437 \u04d9\u0440\u0435\u043a\u0435\u0442\u0456\u04a3\u0456\u0437\u0434\u0456 \u049b\u0430\u0439\u0442\u0430 \u0436\u0430\u0441\u0430\u043f \u043a\u04e9\u0440\u0456\u04a3\u0456\u0437. ",
    "You have selected an action, but you haven\u2019t saved your changes to individual fields yet. Please click OK to save. You\u2019ll need to re-run the action.": "B\u1ea1n \u0111\u00e3 ch\u1ecdn m\u1ed9t h\u00e0nh \u0111\u1ed9ng, nh\u01b0ng b\u1ea1n ch\u01b0a l\u01b0u c\u00e1c thay \u0111\u1ed5i tr\u00ean c\u00e1c tr\u01b0\u1eddng. Vui l\u00f2ng b\u1ea5m OK \u0111\u1ec3 l\u01b0u l\u1ea1i. B\u1ea1n s\u1ebd c\u1ea7n ch\u1ea1y l\u1ea1i h\u00e0nh d\u1ed9ng.",
    "You have unsaved changes on individual editable fields. If you run an action, your unsaved changes will be lost.": "\u0421\u0456\u0437\u0434\u0456\u04a3 \u0442\u04e9\u043c\u0435\u043d\u0434\u0435\u0433\u0456 \u04e9\u0437\u0433\u0435\u0440\u043c\u0435\u043b\u0456 \u0430\u043b\u0430\u04a3\u0434\u0430\u0440\u0434\u0430(fields) \u04e9\u0437\u0433\u0435\u0440\u0456\u0441\u0442\u0435\u0440\u0456\u04a3\u0456\u0437 \u0431\u0430\u0440. \u0415\u0433\u0435\u0440 \u0430\u0440\u0442\u044b\u049b \u04d9\u0440\u0435\u043a\u0435\u0442 \u0436\u0430\u0441\u0430\u0441\u0430\u04a3\u044b\u0437\u0431 \u0441\u0456\u0437 \u04e9\u0437\u0433\u0435\u0440\u0456\u0441\u0442\u0435\u0440\u0456\u04a3\u0456\u0437\u0434\u0456 \u0436\u043e\u0493\u0430\u043b\u0442\u0430\u0441\u044b\u0437.",
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
    "one letter Friday\u0004F": "6",
    "one letter Monday\u0004M": "2",
    "one letter Saturday\u0004S": "7",
    "one letter Sunday\u0004S": "CN",
    "one letter Thursday\u0004T": "5",
    "one letter Tuesday\u0004T": "3",
    "one letter Wednesday\u0004W": "4",
    "past year": "\u04e9\u0442\u043a\u0435\u043d \u0436\u044b\u043b",
    "time format with day\u0004%d day %h:%m:%s": [
      "%d \u043a\u04af\u043d %h:%m:%s",
      "%d \u043a\u04af\u043d %h:%m:%s"
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
    "DATETIME_FORMAT": "N j, Y, P",
    "DATETIME_INPUT_FORMATS": [
      "%Y-%m-%d %H:%M:%S",
      "%Y-%m-%d %H:%M:%S.%f",
      "%Y-%m-%d %H:%M",
      "%m/%d/%Y %H:%M:%S",
      "%m/%d/%Y %H:%M:%S.%f",
      "%m/%d/%Y %H:%M",
      "%m/%d/%y %H:%M:%S",
      "%m/%d/%y %H:%M:%S.%f",
      "%m/%d/%y %H:%M"
    ],
    "DATE_FORMAT": "N j, Y",
    "DATE_INPUT_FORMATS": [
      "%Y-%m-%d",
      "%m/%d/%Y",
      "%m/%d/%y",
      "%b %d %Y",
      "%b %d, %Y",
      "%d %b %Y",
      "%d %b, %Y",
      "%B %d %Y",
      "%B %d, %Y",
      "%d %B %Y",
      "%d %B, %Y"
    ],
    "DECIMAL_SEPARATOR": ".",
    "FIRST_DAY_OF_WEEK": 0,
    "MONTH_DAY_FORMAT": "F j",
    "NUMBER_GROUPING": 0,
    "SHORT_DATETIME_FORMAT": "m/d/Y P",
    "SHORT_DATE_FORMAT": "m/d/Y",
    "THOUSAND_SEPARATOR": ",",
    "TIME_FORMAT": "P",
    "TIME_INPUT_FORMATS": [
      "%H:%M:%S",
      "%H:%M:%S.%f",
      "%H:%M"
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

