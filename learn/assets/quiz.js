/* cloudio course — tiny quiz + free-recall widgets. No dependencies.
   Markup contract:

   <div class="quiz" data-explain="shown after any answer (optional)">
     <p class="quiz-q">Question text</p>
     <button class="quiz-opt" data-correct>Right answer</button>
     <button class="quiz-opt">Wrong answer</button>
     <p class="quiz-fb" hidden></p>
   </div>

   <div class="recall">
     <p>Prompt…</p>
     <textarea></textarea>
     <button>Show a model answer</button>
     <div class="model" hidden>Model answer…</div>
   </div>
*/
(function () {
  "use strict";

  document.querySelectorAll(".quiz").forEach(function (quiz) {
    var opts = Array.prototype.slice.call(quiz.querySelectorAll(".quiz-opt"));
    var fb = quiz.querySelector(".quiz-fb");
    var explain = quiz.getAttribute("data-explain");

    opts.forEach(function (opt) {
      opt.addEventListener("click", function () {
        var correct = opt.hasAttribute("data-correct");
        opts.forEach(function (o) {
          o.disabled = true;
          if (o.hasAttribute("data-correct")) o.classList.add("right");
        });
        if (!correct) opt.classList.add("wrong");
        if (fb) {
          fb.textContent =
            (correct ? "Correct. " : "Not quite. ") + (explain || "");
          fb.hidden = false;
          fb.classList.add("show");
        }
      });
    });
  });

  document.querySelectorAll(".recall").forEach(function (box) {
    var btn = box.querySelector("button");
    var model = box.querySelector(".model");
    if (!btn || !model) return;
    btn.addEventListener("click", function () {
      model.hidden = false;
      btn.disabled = true;
    });
  });
})();
