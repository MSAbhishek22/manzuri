/* Manzuri client page — phone-first, no login. The token in the URL
   is the credential. Plain fetch + DOM, no frameworks. */
(function () {
  "use strict";
  var token = location.pathname.split("/c/")[1] || "";
  var hello = document.getElementById("clientHello");
  var wrap = document.getElementById("clientPosts");
  var done = document.getElementById("clientDone");

  function api(path, opts) {
    return fetch(path, opts).then(function (r) {
      return r.json().then(function (j) {
        if (!r.ok) throw new Error(j.error || "Something went wrong");
        return j;
      });
    });
  }

  function load() {
    api("/api/link/" + token).then(function (data) {
      hello.textContent = "Posts from your agency, " + data.client + ".";
      wrap.innerHTML = "";
      var pending = 0;
      data.posts.forEach(function (post) {
        if (post.status === "pending") pending++;
        wrap.appendChild(card(post));
      });
      if (!data.posts.length) {
        var p = document.createElement("p"); p.className = "muted";
        p.textContent = "No posts yet. Your agency will add them here.";
        wrap.appendChild(p);
      }
      done.hidden = data.posts.length === 0 || pending > 0;
    }).catch(function (err) {
      hello.textContent = err.message;
    });
  }

  function card(post) {
    var el = document.createElement("article"); el.className = "client-post";
    if (post.image_name) {
      var img = document.createElement("img");
      img.src = "/uploads/" + post.image_name; img.alt = "Post creative";
      el.appendChild(img);
    }
    var body = document.createElement("div"); body.className = "body";
    var day = document.createElement("div"); day.className = "day"; day.textContent = post.day_label;
    var cap = document.createElement("p"); cap.className = "caption"; cap.textContent = post.caption || "";
    body.appendChild(day); body.appendChild(cap);

    if (post.status === "approved") {
      var ok = document.createElement("p"); ok.className = "status-line green";
      ok.textContent = "✓ You approved this post.";
      body.appendChild(ok);
    } else if (post.status === "changes") {
      var ch = document.createElement("p"); ch.className = "status-line red";
      ch.textContent = "You asked for changes on this post. Your agency is working on it.";
      body.appendChild(ch);
    } else {
      var row = document.createElement("div"); row.className = "decide-row";
      var approve = document.createElement("button"); approve.type = "button";
      approve.className = "btn-approve"; approve.textContent = "Approve";
      approve.addEventListener("click", function () {
        decide(post.id, { action: "approved" });
      });
      var changes = document.createElement("button"); changes.type = "button";
      changes.className = "btn-changes"; changes.textContent = "Request changes";
      changes.addEventListener("click", function () { showChangeForm(body, post); });
      row.appendChild(approve); row.appendChild(changes);
      body.appendChild(row);
    }
    el.appendChild(body);
    return el;
  }

  function showChangeForm(body, post) {
    if (body.querySelector(".change-form")) return;
    var form = document.createElement("div"); form.className = "change-form";
    var label = document.createElement("p"); label.textContent = "What needs to change?";
    var kinds = document.createElement("div"); kinds.className = "kind-row";
    var chosen = { value: null };
    [["image", "The image"], ["caption", "The words"], ["both", "Both"]].forEach(function (pair) {
      var b = document.createElement("button"); b.type = "button"; b.textContent = pair[1];
      b.setAttribute("aria-pressed", "false");
      b.addEventListener("click", function () {
        chosen.value = pair[0];
        kinds.querySelectorAll("button").forEach(function (x) { x.setAttribute("aria-pressed", "false"); });
        b.setAttribute("aria-pressed", "true");
      });
      kinds.appendChild(b);
    });
    var text = document.createElement("textarea");
    text.placeholder = "Anything else they should know? (optional)";
    var send = document.createElement("button"); send.type = "button";
    send.className = "btn-changes"; send.textContent = "Send to agency";
    send.style.marginTop = ".6rem"; send.style.width = "100%"; send.style.minHeight = "52px";
    send.addEventListener("click", function () {
      if (!chosen.value) { alert("Please pick one: the image, the words, or both."); return; }
      decide(post.id, { action: "changes", note_kind: chosen.value, note_text: text.value || null });
    });
    form.appendChild(label); form.appendChild(kinds); form.appendChild(text); form.appendChild(send);
    body.appendChild(form);
  }

  function decide(postId, payload) {
    payload.post_id = postId;
    api("/api/link/" + token + "/decide", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }).then(load).catch(function (err) { alert(err.message); });
  }

  load();
})();
