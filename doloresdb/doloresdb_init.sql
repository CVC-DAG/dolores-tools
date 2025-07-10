# Create Archive table # # # # # # # # # # # # # # # # # # # #
CREATE TABLE Archive (
  archive_id    VARCHAR(128) NOT NULL,
  archive_name  VARCHAR(255),
  PRIMARY KEY (`archive_id`)
);

# Create Work table # # # # # # # # # # # # # # # # # # # #
CREATE TABLE Work (
  archive_id    	VARCHAR(128) NOT NULL,
  work_id       	VARCHAR(128) NOT NULL,
  composer     		VARCHAR(255),
  copyist     	  	VARCHAR(255),
  composition_year 	INT,
  copy_year 		INT,
  PRIMARY KEY (archive_id, work_id),
  FOREIGN KEY (archive_id) REFERENCES Archive(archive_id)
);

# Create Image table # # # # # # # # # # # # # # # # # # # #
CREATE TABLE Image (
  image_fname       VARCHAR(128) NOT NULL,
  archive_id        VARCHAR(128) NOT NULL,
  work_id           VARCHAR(128) NOT NULL,
  page              INT NOT NULL,
  path_tiff         VARCHAR(255),
  path_jpeg         VARCHAR(255) NOT NULL,
  PRIMARY KEY (image_fname),
  FOREIGN KEY (archive_id, work_id) REFERENCES Work(archive_id, work_id)
);

# Create Line table # # # # # # # # # # # # # # # # # # # #
CREATE TABLE Line (
  line_id       INT NOT NULL,
  image_fname   VARCHAR(128) NOT NULL,
  top_x         INT,
  top_y         INT,
  bot_x         INT,
  bot_y         INT,
  PRIMARY KEY (line_id, image_fname),
  FOREIGN KEY (image_fname) REFERENCES Image(image_fname)
);

# Create Author table # # # # # # # # # # # # # # # # # # # #
CREATE TABLE Author (
  author_email      VARCHAR(255) NOT NULL,
  password          BINARY(64) NOT NULL,
  name              VARCHAR(128) NOT NULL,
  is_admin          BOOL,
  PRIMARY KEY (author_email)
);

# Create LineTranscription table # # # # # # # # # # # # # # # # # # # #
CREATE TABLE LineTranscription (
  line_id               INT NOT NULL,
  transcript_revision   INT NOT NULL,
  image_fname           VARCHAR(128) NOT NULL,
  author                VARCHAR(255) NOT NULL,
  revision_date         TIMESTAMP NOT NULL,
  status                VARCHAR(50) NOT NULL,
  transcription_file    VARCHAR(255) NOT NULL,
  PRIMARY KEY (line_id, transcript_revision, image_fname),
  FOREIGN KEY (line_id, image_fname) REFERENCES Line(line_id, image_fname),
  FOREIGN KEY (author) REFERENCES Author(author_email)
);

# Create Alignment table # # # # # # # # # # # # # # # # # # # #
CREATE TABLE Alignment (
  line_id               INT NOT NULL,
  transcript_revision   INT NOT NULL,
  alignment_revision    INT NOT NULL,
  image_fname           VARCHAR(128) NOT NULL,
  author                VARCHAR(255) NOT NULL,
  revision_date         TIMESTAMP NOT NULL,
  status                VARCHAR(50) NOT NULL,
  transcription_file    VARCHAR(255) NOT NULL,
  PRIMARY KEY (line_id, transcript_revision, alignment_revision, image_fname),
  FOREIGN KEY (line_id, transcript_revision, image_fname) REFERENCES LineTranscription(line_id, transcript_revision, image_fname),
  FOREIGN KEY (author) REFERENCES Author(author_email)
);
