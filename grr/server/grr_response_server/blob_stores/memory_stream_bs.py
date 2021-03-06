#!/usr/bin/env python
"""A blob store based on memory stream objects."""
from __future__ import unicode_literals

import hashlib
import logging


from future.utils import iteritems
from future.utils import iterkeys

from grr_response_core.lib import rdfvalue
from grr_response_server import aff4
from grr_response_server import blob_store
from grr_response_server import data_store


class MemoryStreamBlobstore(blob_store.Blobstore):
  """A blob store based on memory streams for backwards compatibility."""

  def _BlobUrn(self, digest):
    return rdfvalue.RDFURN("aff4:/blobs").Add(digest)

  def StoreBlobs(self, contents, token=None):
    """Creates or overwrites blobs."""

    contents_by_digest = {
        hashlib.sha256(content).hexdigest(): content for content in contents
    }

    urns = {self._BlobUrn(digest): digest for digest in contents_by_digest}

    mutation_pool = data_store.DB.GetMutationPool()

    existing = aff4.FACTORY.MultiOpen(
        urns, aff4_type=aff4.AFF4MemoryStreamBase, mode="r", token=token)

    for blob_urn, digest in iteritems(urns):
      if blob_urn in existing:
        logging.debug("Blob %s already stored.", digest)
        continue

      fd = aff4.FACTORY.Create(
          blob_urn,
          aff4.AFF4UnversionedMemoryStream,
          mode="w",
          token=token,
          mutation_pool=mutation_pool)
      content = contents_by_digest[digest]
      fd.Write(content)
      fd.Close()

      logging.debug("Got blob %s (length %s)", digest, len(content))

    mutation_pool.Flush()

    return list(iterkeys(contents_by_digest))

  def ReadBlobs(self, digests, token=None):
    res = {digest: None for digest in digests}
    urns = {self._BlobUrn(digest): digest for digest in digests}

    fds = aff4.FACTORY.MultiOpen(urns, mode="r", token=token)

    for fd in fds:
      res[urns[fd.urn]] = fd.read()

    return res

  def BlobsExist(self, digests, token=None):
    """Check if blobs for the given digests already exist."""
    res = {digest: False for digest in digests}

    urns = {self._BlobUrn(digest): digest for digest in digests}

    existing = aff4.FACTORY.MultiOpen(
        urns, aff4_type=aff4.AFF4MemoryStreamBase, mode="r", token=token)

    for blob in existing:
      res[urns[blob.urn]] = True

    return res
