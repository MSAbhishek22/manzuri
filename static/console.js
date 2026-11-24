/* Manzuri agency console. */
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var current = null; // selected client object
  var wall = new window.MonthWall($("wall"));

  function api(path, opts) {
    return fetch(path, opts).then(function (r) {
      return r.json().then(function (j) {
        if (!r.ok) throw new Error(j.error || "Request failed");
        return j;
      });
    });
  }

  function refreshClients() {
    return api("/api/clients").then(function (clients) {
      var totals = { waiting: 0, approved: 0, changes: 0 };
      var list = $("clientList");
      list.innerHTML = "";
      clients.forEach(function (c) {
        totals.waiting += c.pending || 0;
        totals.approved += c.approved || 0;
        totals.changes += c.changes || 0;
        var btn = document.createElement("button");
        btn.type = "button"; btn.className = "client-row";
        var left = document.createElement("span");
        left.textContent = c.name;
        var right = document.createElement("span"); right.className = "muted";
        right.textContent = (c.posts || 0) + " posts · " + (c.approved || 0) + " approved · " +
          (c.pending || 0) + " waiting · " + (c.changes || 0) + " changes";
        btn.appendChild(left); btn.appendChild(right);
        btn.addEventListener("click", function () { openClient(c); });
        list.appendChild(btn);
      });
      $("countWaiting").textContent = totals.waiting;
      $("countApproved").textContent = totals.approved;
      $("countChanges").textContent = totals.changes;
      if (current) {
        var fresh = clients.filter(function (c) { return c.id === current.id; })[0];
        if (fresh) current = fresh;
      }
    });
  }

  function openClient(client) {
    current = client;
    $("clientPanel").hidden = false;
    $("panelTitle").textContent = client.name;
    var link = location.origin + "/c/" + client.token;
    $("linkBox").value = link;
    $("waSend").href = "https://wa.me/?text=" + encodeURIComponent(
      "Namaste! Your posts for this month are ready for a quick look. " +
      "Please approve or tell us what to change — no login needed: " + link);
    $("exportLink").href = "/api/clients/" + client.id + "/export";
    refreshPosts();
  }

  function refreshPosts() {
    if (!current) return;
    api("/api/clients/" + current.id + "/posts").then(function (posts) {
      wall.setPosts(posts);
      var list = $("postList");
      list.innerHTML = "";
      if (!posts.length) {
        var p = document.createElement("p"); p.className = "muted";
        p.textContent = "No posts yet. Add the month's posts above — then send the client their link.";
        list.appendChild(p);
      }
      posts.forEach(function (post) { list.appendChild(postCard(post)); });
    }).catch(showError);
  }

  function postCard(post) {
    var card = document.createElement("div"); card.className = "post-card"; card.id = "post-" + post.id;
    if (post.image_name) {
      var img = document.createElement("img");
      img.src = "/uploads/" + post.image_name; img.alt = "Creative for " + post.day_label;
      card.appendChild(img);
    }
    var main = document.createElement("div"); main.className = "post-main";
    var head = document.createElement("div");
    var day = document.createElement("span"); day.className = "post-day"; day.textContent = post.day_label;
    var chip = document.createElement("span"); chip.className = "chip " + post.status;
    chip.textContent = post.status === "approved" ? "Approved · v" + post.version
      : post.status === "changes" ? "Changes requested" : "Waiting · v" + post.version;
    head.appendChild(day); head.appendChild(chip);
    var cap = document.createElement("p"); cap.textContent = post.caption || "(no caption)";
    var actions = document.createElement("div"); actions.className = "post-actions";
    var editBtn = document.createElement("button"); editBtn.type = "button"; editBtn.textContent = "Edit post";
    editBtn.addEventListener("click", function () { showEdit(post, main); });
    actions.appendChild(editBtn);
    main.appendChild(head); main.appendChild(cap); main.appendChild(actions);
    card.appendChild(main);
    return card;
  }

  function showEdit(post, main) {
    var box = document.createElement("div");
    var note = document.createElement("p"); note.className = "history";
    note.textContent = post.status !== "pending"
      ? "Careful: saving an edit will VOID the client's current decision on this post and send it back to waiting."
      : "Editing bumps the version. The client always approves a specific version.";
    var cap = document.createElement("input"); cap.type = "text"; cap.value = post.caption;
    var file = document.createElement("input"); file.type = "file";
    file.accept = "image/png,image/jpeg,image/webp,image/gif";
    var save = document.createElement("button"); save.type = "button"; save.className = "primary"; save.textContent = "Save edit";
    save.addEventListener("click", function () {
      var fd = new FormData();
      fd.append("caption", cap.value);
      if (file.files[0]) fd.append("image", file.files[0]);
      api("/api/posts/" + post.id + "/edit", { method: "POST", body: fd })
        .then(function (res) {
          if (res.voided) alert("Saved. The earlier approval was voided — the client will see the new version as waiting.");
          refreshPosts(); refreshClients();
        }).catch(showError);
    });
    box.appendChild(note); box.appendChild(cap); box.appendChild(file); box.appendChild(save);
    main.appendChild(box);
  }

  function showError(err) { alert(err.message || String(err)); }

  $("clientForm").addEventListener("submit", function (ev) {
    ev.preventDefault();
    api("/api/clients", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: $("clientName").value })
    }).then(function (client) {
      $("clientName").value = "";
      refreshClients().then(function () { openClient(client); });
    }).catch(showError);
  });

  $("postForm").addEventListener("submit", function (ev) {
    ev.preventDefault();
    if (!current) return;
    var fd = new FormData();
    fd.append("day_label", $("postDay").value);
    fd.append("caption", $("postCaption").value);
    if ($("postImage").files[0]) fd.append("image", $("postImage").files[0]);
    api("/api/clients/" + current.id + "/posts", { method: "POST", body: fd })
      .then(function () {
        $("postDay").value = ""; $("postCaption").value = ""; $("postImage").value = "";
        refreshPosts(); refreshClients();
      }).catch(showError);
  });

  $("copyLink").addEventListener("click", function () {
    $("linkBox").select();
    navigator.clipboard && navigator.clipboard.writeText($("linkBox").value);
    $("copyLink").textContent = "Copied";
    setTimeout(function () { $("copyLink").textContent = "Copy link"; }, 1500);
  });

  refreshClients().catch(showError);
})();
