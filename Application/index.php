<!DOCTYPE html>
<html lang="pt-br">

  <head>
    <meta charset="UTF-8">
    <meta name='viewport' content='width=device-width, initial-scale=1'>
	
	<link rel="preconnect" href="https://fonts.googleapis.com">
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
	<link href="https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,100..900;1,14..32,100..900&display=swap" rel="stylesheet">

    <link rel='stylesheet'
      href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css'>

    <style>
        * {
          margin: 0px;
          padding: 0px;
        }

        body {
          background-color: #d6d6d6;
		  font-family: "Inter", sans-serif;
		  font-optical-sizing: auto;
		  font-style: normal;
		  font-weight: 400;
        }

        .bg-cover {
          background-image: url("https://picsum.photos/1920/1080");
          background-size: cover;
          background-position: center center;
          background-repeat: no-repeat;
          width: 100vw;
          height: 100vh;
        }

        .bg-cover::before {
          content: "";
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: rgba(0, 0, 0, 0.8); /* overlay 80% preto */
          z-index: 1;
        }

        .bg-cover > * {
          position: relative;
          z-index: 2;
        }

      </style>

    <title>Bem-Vindo</title>

  </head>

  <body>

    <div
      class="container-fluid bg-cover d-flex align-items-center justify-content-center">
      <h1
        class="text-uppercase fw-bold shadow bg-primary text-white p-3 border border-primary rounded rounded-2">
        Bem-vindo!
      </h1>
    </div>

    <script
      src='https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.min.js'></script>
    <script
      src='https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js'></script>
  </body>

</html>