

'use strict';
{
  const globals = this;
  const django = globals.django || (globals.django = {});

  
  django.pluralidx = function(n) {
    const v = 0;
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
      "%(year)d \u5e74\u6709 %(cnt)d \u4efd\u63d0\u4ea4\u7d00\u9304"
    ],
    "%(cnt)d submission in the last year": [
      "\u9019\u4e00\u5e74\u4f86\u63d0\u4ea4\u4e86 %(cnt)d \u6b21\u7b54\u6848"
    ],
    "%(cnt)d submission on %(date)s": [
      "%(date)s \u6709 %(cnt)d \u4efd\u63d0\u4ea4\u7d00\u9304"
    ],
    "%(cnt)d total submission": [
      "%(cnt)d \u4efd\u63d0\u4ea4\u7d00\u9304"
    ],
    "%(sel)s of %(cnt)s selected": [
      "%(cnt)s \u4e2d %(sel)s \u500b\u88ab\u9078"
    ],
    "6 a.m.": "\u4e0a\u5348 6 \u9ede",
    "6 p.m.": "\u4e0b\u5348 6 \u9ede",
    "April": "\u56db\u6708",
    "August": "\u516b\u6708",
    "Available %s": "\u53ef\u7528 %s",
    "Cancel": "\u53d6\u6d88",
    "Choose": "\u9078\u53d6",
    "Choose a Date": "\u9078\u64c7\u4e00\u500b\u65e5\u671f",
    "Choose a Time": "\u9078\u64c7\u4e00\u500b\u6642\u9593",
    "Choose a time": "\u9078\u64c7\u4e00\u500b\u6642\u9593",
    "Choose all": "\u5168\u9078",
    "Chosen %s": "%s \u88ab\u9078",
    "Click to choose all %s at once.": "\u9ede\u64ca\u4ee5\u4e00\u6b21\u9078\u53d6\u6240\u6709\u7684 %s",
    "Click to remove all chosen %s at once.": "\u9ede\u64ca\u4ee5\u4e00\u6b21\u79fb\u9664\u6240\u6709\u9078\u53d6\u7684 %s",
    "December": "\u5341\u4e8c\u6708",
    "Edit points vote (%s)": "S\u1eeda \u0111i\u1ec3m vote (%s)",
    "February": "\u4e8c\u6708",
    "Filter": "\u904e\u6ffe\u5668",
    "Hide": "\u96b1\u85cf",
    "January": "\u4e00\u6708",
    "July": "\u4e03\u6708",
    "June": "\u516d\u6708",
    "March": "\u4e09\u6708",
    "May": "\u4e94\u6708",
    "Midnight": "\u5348\u591c",
    "Noon": "\u4e2d\u5348",
    "Note: You are %s hour ahead of server time.": [
      "\u5099\u8a3b\uff1a\u60a8\u7684\u96fb\u8166\u6642\u9593\u6bd4\u4f3a\u670d\u5668\u5feb %s \u5c0f\u6642\u3002"
    ],
    "Note: You are %s hour behind server time.": [
      "\u5099\u8a3b\uff1a\u60a8\u7684\u96fb\u8166\u6642\u9593\u6bd4\u4f3a\u670d\u5668\u6162 %s \u5c0f\u6642\u3002"
    ],
    "November": "\u5341\u4e00\u6708",
    "Now": "\u73fe\u5728",
    "Number of votes for this point value": "S\u1ed1 l\u01b0\u1ee3ng b\u00ecnh ch\u1ecdn cho \u0111i\u1ec3m n\u00e0y",
    "October": "\u5341\u6708",
    "Remove": "\u79fb\u9664",
    "Remove all": "\u5168\u90e8\u79fb\u9664",
    "September": "\u4e5d\u6708",
    "Show": "\u986f\u793a",
    "This is the list of available %s. You may choose some by selecting them in the box below and then clicking the \"Choose\" arrow between the two boxes.": "\u53ef\u7528\u7684 %s \u5217\u8868\u3002\u4f60\u53ef\u4ee5\u5728\u4e0b\u65b9\u7684\u65b9\u6846\u5167\u9078\u64c7\u5f8c\uff0c\u9ede\u64ca\u5169\u500b\u65b9\u6846\u4e2d\u7684\"\u9078\u53d6\"\u7bad\u982d\u4ee5\u9078\u53d6\u3002",
    "This is the list of chosen %s. You may remove some by selecting them in the box below and then clicking the \"Remove\" arrow between the two boxes.": "\u9078\u53d6\u7684 %s \u5217\u8868\u3002\u4f60\u53ef\u4ee5\u5728\u4e0b\u65b9\u7684\u65b9\u6846\u5167\u9078\u64c7\u5f8c\uff0c\u9ede\u64ca\u5169\u500b\u65b9\u6846\u4e2d\u7684\"\u79fb\u9664\"\u7bad\u982d\u4ee5\u79fb\u9664\u3002",
    "Today": "\u4eca\u5929",
    "Tomorrow": "\u660e\u5929",
    "Type into this box to filter down the list of available %s.": "\u8f38\u5165\u5230\u9019\u500b\u65b9\u6846\u4ee5\u904e\u6ffe\u53ef\u7528\u7684 %s \u5217\u8868\u3002",
    "Unable to cast vote: %s": "Kh\u00f4ng th\u1ec3 s\u1eeda \u0111i\u1ec3m: %s",
    "Unable to delete vote: %s": "Kh\u00f4ng th\u1ec3 s\u1eeda \u0111i\u1ec3m: %s",
    "Vote on problem points": "B\u00ecnh ch\u1ecdn \u0111i\u1ec3m c\u1ee7a b\u00e0i t\u1eadp",
    "Yesterday": "\u6628\u5929",
    "You have selected an action, and you haven't made any changes on individual fields. You're probably looking for the Go button rather than the Save button.": "\u4f60\u5df2\u9078\u4e86\u4e00\u500b\u52d5\u4f5c, \u4f46\u6c92\u6709\u4efb\u4f55\u6539\u8b8a\u3002\u4f60\u53ef\u80fd\u52d5\u5230 '\u53bb' \u6309\u9215, \u800c\u4e0d\u662f '\u5132\u5b58' \u6309\u9215\u3002",
    "You have selected an action, and you haven\u2019t made any changes on individual fields. You\u2019re probably looking for the Go button rather than the Save button.": "B\u1ea1n \u0111\u00e3 ch\u1ecdn m\u1ed9t h\u00e0nh \u0111\u1ed9ng v\u00e0 b\u1ea1n \u0111\u00e3 kh\u00f4ng th\u1ef1c hi\u1ec7n b\u1ea5t k\u1ef3 thay \u0111\u1ed5i n\u00e0o tr\u00ean c\u00e1c tr\u01b0\u1eddng. C\u00f3 l\u1ebd b\u1ea1n n\u00ean b\u1ea5m n\u00fat \u0110i \u0111\u1ebfn h\u01a1n l\u00e0 n\u00fat L\u01b0u l\u1ea1i.",
    "You have selected an action, but you haven't saved your changes to individual fields yet. Please click OK to save. You'll need to re-run the action.": "\u4f60\u5df2\u9078\u4e86\u4e00\u500b\u52d5\u4f5c, \u4f46\u6709\u4e00\u500b\u53ef\u7de8\u8f2f\u6b04\u4f4d\u7684\u8b8a\u66f4\u5c1a\u672a\u5132\u5b58\u3002\u8acb\u9ede\u9078 OK \u9032\u884c\u5132\u5b58\u3002\u4f60\u9700\u8981\u91cd\u65b0\u57f7\u884c\u8a72\u52d5\u4f5c\u3002",
    "You have selected an action, but you haven\u2019t saved your changes to individual fields yet. Please click OK to save. You\u2019ll need to re-run the action.": "B\u1ea1n \u0111\u00e3 ch\u1ecdn m\u1ed9t h\u00e0nh \u0111\u1ed9ng, nh\u01b0ng b\u1ea1n ch\u01b0a l\u01b0u c\u00e1c thay \u0111\u1ed5i tr\u00ean c\u00e1c tr\u01b0\u1eddng. Vui l\u00f2ng b\u1ea5m OK \u0111\u1ec3 l\u01b0u l\u1ea1i. B\u1ea1n s\u1ebd c\u1ea7n ch\u1ea1y l\u1ea1i h\u00e0nh d\u1ed9ng.",
    "You have unsaved changes on individual editable fields. If you run an action, your unsaved changes will be lost.": "\u4f60\u5c1a\u672a\u5132\u5b58\u4e00\u500b\u53ef\u7de8\u8f2f\u6b04\u4f4d\u7684\u8b8a\u66f4\u3002\u5982\u679c\u4f60\u57f7\u884c\u52d5\u4f5c, \u672a\u5132\u5b58\u7684\u8b8a\u66f4\u5c07\u6703\u907a\u5931\u3002",
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
    "one letter Friday\u0004F": "\u4e94",
    "one letter Monday\u0004M": "\u4e00",
    "one letter Saturday\u0004S": "\u516d",
    "one letter Sunday\u0004S": "\u65e5",
    "one letter Thursday\u0004T": "\u56db",
    "one letter Tuesday\u0004T": "\u4e8c",
    "one letter Wednesday\u0004W": "\u4e09",
    "past year": "\u53bb\u5e74",
    "time format with day\u0004%d day %h:%m:%s": [
      "%d \u5929 %h:%m:%s"
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
    "DATETIME_FORMAT": "Y\u5e74n\u6708j\u65e5 H:i",
    "DATETIME_INPUT_FORMATS": [
      "%Y/%m/%d %H:%M",
      "%Y-%m-%d %H:%M",
      "%Y\u5e74%n\u6708%j\u65e5 %H:%M",
      "%Y/%m/%d %H:%M:%S",
      "%Y-%m-%d %H:%M:%S",
      "%Y\u5e74%n\u6708%j\u65e5 %H:%M:%S",
      "%Y/%m/%d %H:%M:%S.%f",
      "%Y-%m-%d %H:%M:%S.%f",
      "%Y\u5e74%n\u6708%j\u65e5 %H:%n:%S.%f",
      "%Y-%m-%d"
    ],
    "DATE_FORMAT": "Y\u5e74n\u6708j\u65e5",
    "DATE_INPUT_FORMATS": [
      "%Y/%m/%d",
      "%Y-%m-%d",
      "%Y\u5e74%n\u6708%j\u65e5"
    ],
    "DECIMAL_SEPARATOR": ".",
    "FIRST_DAY_OF_WEEK": 1,
    "MONTH_DAY_FORMAT": "m\u6708j\u65e5",
    "NUMBER_GROUPING": 4,
    "SHORT_DATETIME_FORMAT": "Y\u5e74n\u6708j\u65e5 H:i",
    "SHORT_DATE_FORMAT": "Y\u5e74n\u6708j\u65e5",
    "THOUSAND_SEPARATOR": "",
    "TIME_FORMAT": "H:i",
    "TIME_INPUT_FORMATS": [
      "%H:%M",
      "%H:%M:%S",
      "%H:%M:%S.%f"
    ],
    "YEAR_MONTH_FORMAT": "Y\u5e74n\u6708"
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

