/* Manzuri "Month Wall" — the client's month as standing tiles in a
   shallow arc (Three.js, agency console only). Posture is state:
   upright + white = waiting, lying back + green = approved,
   tilted forward + red edge = changes requested. Clicking a tile
   scrolls to the post. Falls back silently: the counts and list
   above/below carry the same information in text. */
(function () {
  "use strict";
  function MonthWall(canvas) {
    this.canvas = canvas;
    this.posts = [];
    if (typeof THREE === "undefined") return;
    try {
      this.renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true });
      this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
      this.scene = new THREE.Scene();
      this.scene.background = new THREE.Color(0xf1ede3);
      this.camera = new THREE.PerspectiveCamera(38, 2, 0.1, 100);
      this.camera.position.set(0, 3.4, 11);
      this.camera.lookAt(0, 0.6, 0);
      this.scene.add(new THREE.AmbientLight(0xffffff, 0.75));
      var key = new THREE.DirectionalLight(0xffffff, 0.8);
      key.position.set(4, 8, 6); this.scene.add(key);
      this.group = new THREE.Group(); this.scene.add(this.group);
      this.raycaster = new THREE.Raycaster();
      this.tiles = [];
      var self = this;
      canvas.addEventListener("click", function (ev) { self._click(ev); });
      window.addEventListener("resize", function () { self._resize(); self._render(); });
      this._resize();
    } catch (err) { this.renderer = null; }
  }
  MonthWall.prototype.setPosts = function (posts) {
    this.posts = posts || [];
    if (!this.renderer) return;
    /* The canvas starts inside a hidden panel, so its size at
       construction time is 0 — re-measure now that it is visible. */
    this._resize();
    while (this.group.children.length) {
      var c = this.group.children.pop();
      if (c.geometry) c.geometry.dispose();
    }
    this.tiles = [];
    var n = Math.min(this.posts.length, 31);
    var geo = new THREE.BoxGeometry(0.92, 1.35, 0.1);
    for (var i = 0; i < n; i++) {
      var post = this.posts[i];
      var t = n === 1 ? 0 : (i / (n - 1) - 0.5);
      var color = post.status === "approved" ? 0x0e7a5f
        : post.status === "changes" ? 0xd8cfc0 : 0xffffff;
      var mat = new THREE.MeshStandardMaterial({ color: color, roughness: 0.6 });
      var tile = new THREE.Mesh(geo, mat);
      tile.position.set(t * 13, 0.75, -Math.abs(t) * 1.6);
      tile.rotation.y = -t * 0.55;
      if (post.status === "approved") { tile.rotation.x = -1.15; tile.position.y = 0.35; }
      if (post.status === "changes") {
        tile.rotation.x = 0.5;
        var edge = new THREE.Mesh(new THREE.BoxGeometry(0.98, 0.1, 0.12),
          new THREE.MeshBasicMaterial({ color: 0xc8372d }));
        edge.position.y = 0.68; tile.add(edge);
      }
      tile.userData.postId = post.id;
      this.group.add(tile); this.tiles.push(tile);
    }
    this._render();
  };
  MonthWall.prototype._click = function (ev) {
    var rect = this.canvas.getBoundingClientRect();
    var mouse = new THREE.Vector2(
      ((ev.clientX - rect.left) / rect.width) * 2 - 1,
      -((ev.clientY - rect.top) / rect.height) * 2 + 1);
    this.raycaster.setFromCamera(mouse, this.camera);
    var hits = this.raycaster.intersectObjects(this.tiles);
    if (hits.length) {
      var el = document.getElementById("post-" + hits[0].object.userData.postId);
      if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  };
  MonthWall.prototype._resize = function () {
    if (!this.renderer) return;
    this.renderer.setSize(this.canvas.clientWidth, this.canvas.clientHeight, false);
    this.camera.aspect = this.canvas.clientWidth / this.canvas.clientHeight;
    this.camera.updateProjectionMatrix();
  };
  MonthWall.prototype._render = function () {
    if (this.renderer) this.renderer.render(this.scene, this.camera);
  };
  window.MonthWall = MonthWall;
})();
