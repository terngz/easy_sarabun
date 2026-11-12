/* Easy Sarabun Web — digit conversion core.
 * Self-contained JS port of the pure-Python logic in engine.py.
 * NOTE: This is a NEW web implementation. It does NOT modify or depend on
 * the original Python engine.py; it reproduces the same transform in JS.
 */
(function (global) {
  'use strict';

  var ARABIC = '0123456789';
  var THAI = '\u0E50\u0E51\u0E52\u0E53\u0E54\u0E55\u0E56\u0E57\u0E58\u0E59'; // ๐-๙
  var THAI_ZERO = 0x0E50;
  var THAI_NINE = 0x0E59;

  /** 0-9 -> ๐-๙ */
  function to_thai(text) {
    if (!text) return '';
    var re = /[0-9]/g;
    return text.replace(re, function (d) {
      return THAI[ARABIC.indexOf(d)];
    });
  }

  /** ๐-๙ -> 0-9 */
  function to_arabic(text) {
    if (!text) return '';
    var re = /[\u0E50-\u0E59]/g;
    return text.replace(re, function (d) {
      return String(d.charCodeAt(0) - THAI_ZERO);
    });
  }

  /** reverse=false: อารบิก -> ไทย | reverse=true: ไทย -> อารบิก */
  function get_converter(reverse) {
    return reverse ? to_arabic : to_thai;
  }

  global.EasyEngine = {
    to_thai: to_thai,
    to_arabic: to_arabic,
    get_converter: get_converter,
    THAI_ZERO: THAI_ZERO,
    THAI_NINE: THAI_NINE
  };
})(window);
